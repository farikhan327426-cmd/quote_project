import asyncio
import os
import sys
import time
from typing import List, Optional, Any, Dict
from contextlib import asynccontextmanager
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, HTTPException, Request, Depends, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# --- IMPORTS ---
from agenticAI_full_workflow.agent.agent_workflow import AgentWorkflowBuilder
from shared_core.logger.logging import logger
from shared_core.exception.exceptionhandling import CustomException

# --- CONFIG ---
load_dotenv(find_dotenv(), override=True)

POSTGRES_URL = os.getenv("POSTGRES_URL")
API_KEY = os.getenv("AGENT_API_KEY") 

if not API_KEY:
    logger.error("CRITICAL: AGENT_API_KEY is missing! Application cannot start safely.")
    sys.exit(1)

# [FIX]: Removed WindowsSelectorEventLoopPolicy
# It breaks MCP subprocesses on Windows. Default 'Proactor' loop is better for MCP.

# --- LIFECYCLE & STATE ---
class ServiceState:
    pool: Optional[AsyncConnectionPool] = None
    checkpointer: Optional[AsyncPostgresSaver] = None

service_state = ServiceState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Agent API (Production Mode)...")
    
    if not POSTGRES_URL:
        logger.error("CRITICAL: POSTGRES_URL is missing.")
        sys.exit(1)

    try:
        service_state.pool = AsyncConnectionPool(conninfo=POSTGRES_URL, max_size=20)
        await service_state.pool.open()
        logger.info("Database Connection Pool Created.")

        service_state.checkpointer = AsyncPostgresSaver(service_state.pool)
        await service_state.checkpointer.setup()
        logger.info("Checkpointer Initialized.")
        
        yield
        
    except Exception as e:
        logger.error(f"Critical Startup Error: {e}")
        sys.exit(1)
    finally:
        logger.info("Shutting down...")
        if service_state.pool:
            await service_state.pool.close()
            logger.info("Database Pool Closed.")

# --- FASTAPI APP ---
app = FastAPI(
    title="Quote & Order Agent API", 
    version="2.1.0 (Fixed)",
    lifespan=lifespan
)

# --- MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", str(int(time.time()*1000)))
    logger.info(f"[Req:{request_id}] {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(f"[Req:{request_id}] {response.status_code} ({process_time:.2f}ms)")
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(f"[Req:{request_id}] FAILED ({process_time:.2f}ms): {e}")
        raise e

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID", "unknown")
    if not isinstance(exc, CustomException):
        ce = CustomException(exc, sys)
    else:
        ce = exc
    logger.error(f"[Req:{request_id}] Critical Unhandled Exception: {ce}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "request_id": request_id}
    )

# --- SECURITY ---
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=403, detail="Missing X-API-Key Header")
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid Credentials")
    return api_key

# --- MODELS ---
class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    quote_id: Optional[str] = None 

class ApprovalRequest(BaseModel):
    thread_id: str

class ChatResponse(BaseModel):
    thread_id: str
    response: str
    current_node: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    is_paused: bool = False
    missing_fields: Optional[List[str]] = None

# --- HELPERS ---
async def build_graph_for_request(checkpointer: AsyncPostgresSaver):
    builder = AgentWorkflowBuilder()
    graph = await builder.build(checkpointer=checkpointer)
    return graph

# --- ENDPOINTS ---

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, token: str = Depends(verify_api_key)):
    thread_id = request.thread_id or f"session_{int(time.time())}"
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"Chat Request [Thread: {thread_id}]")

    try:
        graph = await build_graph_for_request(service_state.checkpointer)
        snapshot = await graph.aget_state(config)
        
        # Handle Silent ID Injection
        if not snapshot.created_at:
            msg = ("user", request.message)
            initial_data = {}
            if request.quote_id:
                logger.info(f"[Thread: {thread_id}] Injecting Silent Quote ID: {request.quote_id}")
                initial_data["key"] = request.quote_id 

            payload = {
                "messages": [msg], 
                "is_approved": False,
                "extracted_data": initial_data 
            }
        else:
             # Resume logic
            if snapshot.next and "Review_Gate" in snapshot.next:
                 payload = {"messages": [("user", request.message)], "is_approved": False}
            else:
                payload = {"messages": [("user", request.message)]}
        
        await graph.ainvoke(payload, config)
        
        return await _format_response(graph, config, thread_id)
        
    except Exception as e:
        raise e

@app.post("/approve", response_model=ChatResponse)
async def approve_order(request: ApprovalRequest, token: str = Depends(verify_api_key)):
    """
    Approves the order. Returns the FINAL response (including Price).
    """
    thread_id = request.thread_id
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"Approval Request [Thread: {thread_id}]")
    
    try:
        graph = await build_graph_for_request(service_state.checkpointer)
        
        snapshot = await graph.aget_state(config)
        if not snapshot.next or "Review_Gate" not in snapshot.next:
            raise HTTPException(status_code=400, detail="Workflow is not at Review Gate.")
            
        # 1. Update State
        await graph.aupdate_state(config, {"is_approved": True})
        
        # 2. Resume Graph (This triggers Submitter -> MCP)
        await graph.ainvoke(None, config)
        
        # 3. Fetch Final State (Should contain the Quote Message)
        return await _format_response(graph, config, thread_id)
        
    except HTTPException:
        raise
    except Exception as e:
        raise e

# Helper to avoid code duplication
async def _format_response(graph, config, thread_id):
    final_snapshot = await graph.aget_state(config)
    
    # Logic to extract the LAST message (which contains the quote)
    messages = final_snapshot.values.get("messages", [])
    response_text = ""
    
    if messages:
        last_msg = messages[-1]
        # Ensure we capture content even if it's a generic BaseMessage
        if hasattr(last_msg, "content"):
            response_text = last_msg.content
    
    if not response_text:
        response_text = "Processing complete."

    is_paused = False
    if final_snapshot.next and "Review_Gate" in final_snapshot.next:
        is_paused = True
        response_text = "Review required. Please check extracted data."

    logger.info(f"Response for {thread_id}: {response_text[:50]}...")

    return ChatResponse(
        thread_id=thread_id,
        response=str(response_text),
        current_node=final_snapshot.next[0] if final_snapshot.next else None,
        extracted_data=final_snapshot.values.get("extracted_data"),
        is_paused=is_paused,
        missing_fields=final_snapshot.values.get("missing_fields", [])
    )

@app.get("/health")
def health_check():
    if service_state.pool and not service_state.pool.closed:
        return {"status": "ok", "db": "connected"}
    return JSONResponse(status_code=503, content={"status": "degraded", "db": "disconnected"})