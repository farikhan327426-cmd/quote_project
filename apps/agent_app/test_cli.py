import asyncio
import sys
import time
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from shared_core.logger.logging import logger

# --- IMPORTS ---
# IMPORTS
# New: Installed Package dependency - works from anywhere
from agenticAI_full_workflow.agent.agent_workflow import AgentWorkflowBuilder

# Load .env
load_dotenv(find_dotenv(), override=True)
logger.info("Loading project...")

# Fix for psycopg/asyncio on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- HELPER FUNCTIONS ---

async def ainput(prompt: str = "") -> str:
    """Async wrapper for input() to avoid blocking."""
    return await asyncio.to_thread(input, prompt)

def print_header(title: str):
    print(f"\n{'='*50}")
    print(f"       {title.center(36)}       ")
    print(f"{'='*50}")

def print_step(message: str):
    print(f"\n[SYSTEM]: {message}")

def print_agent_msg(content: str):
    print(f"\n[ASSISTANT]: {content}")

def print_error(message: str):
    print(f"\n[ERROR]: {message}")

# --- MAIN INTERACTIVE LOOP ---

async def run_interactive():
    print_header("INTERACTIVE AGENT WORKFLOW CLI")
    
    # --- POSTGRES SETUP ---
    postgres_url = os.getenv("POSTGRES_URL")
    if not postgres_url:
        print_error("POSTGRES_URL not found in .env")
        return

    # Use AsyncConnectionPool for efficient connections
    # from psycopg_pool import AsyncConnectionPool # Not needed if using from_conn_string
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    print("[INIT]: Connecting to PostgreSQL...")
    
    # Use context manager to manage pool automatically
    async with AsyncPostgresSaver.from_conn_string(postgres_url) as checkpointer:
        
        # Ensure tables exist
        await checkpointer.setup()
        
        print("[INIT]: Building Agent Workflow with Postgres persistence...")
        try:
            builder = AgentWorkflowBuilder()
            # Pass the postgres checkpointer
            graph = await builder.build(checkpointer=checkpointer)
        except Exception as e:
            print_error(f"Failed to build workflow: {e}")
            return

        # Generate a unique thread ID
        # For persistence to be useful, we might ideally reuse this across runs, 
        # but for this interactive session we'll start a new one or allow user to specify.
        current_time = int(time.time())
        thread_id = f"interactive_session_{current_time}"
        config = {"configurable": {"thread_id": thread_id}}
        print(f"[INIT]: Session ID: {thread_id}")

        # Initial Input
        user_input = await ainput("\n>>> Enter your request: ")
        if not user_input.strip():
            print("[WARN]: Empty input provided. Using default test data.")
            user_input = "I want to ship 50kg from New York to London."
            print(f"[INFO]: Input set to: {user_input}")

        print_step("Processing... (Scout -> Agent -> Inspector -> Review Gate)")
        
        # 1. Start the workflow
        initial_payload = {
            "messages": [("user", user_input)], 
            "is_approved": False
        }
        
        await graph.ainvoke(initial_payload, config)
        
        # 2. Main Event Loop
        while True:
            snapshot = await graph.aget_state(config)
            
            if snapshot.next:
                if "Review_Gate" in snapshot.next:
                    print("\n--------------------------------------------------")
                    print("🛑 STEP: HUMAN REVIEW GATE")
                    print("--------------------------------------------------")
                    
                    extracted = snapshot.values.get('extracted_data', {})
                    missing = snapshot.values.get('missing_fields', [])
                    
                    print(f"📝 Extracted Data:")
                    import json
                    print(json.dumps(extracted, indent=2))
                    
                    if missing:
                        print(f"\n⚠️ Missing Fields: {missing}")
                    else:
                        print(f"\n✅ All required fields seem present.")
                    
                    print("\n[OPTIONS]:")
                    print(" [1] Approve & Submit")
                    print(" [2] Reject & Correct (Provide feedback)")
                    print(" [q] Quit")
                    
                    choice = await ainput("\nSelect Option [1/2/q]: ")
                    
                    if choice == "1":
                        print("\n[ACTION]: Approving data...")
                        await graph.aupdate_state(config, {"is_approved": True})
                        print_step("Resuming workflow (Proceeding to Submitter)...")
                        await graph.ainvoke(None, config)
                        
                    elif choice == "2":
                        print("\n[ACTION]: Rejecting data.")
                        feedback = await ainput("Enter your correction/feedback: ")
                        if not feedback.strip():
                            feedback = "Please double check the data."
                        
                        print_step(f"Sending feedback to Agent: '{feedback}'")
                        await graph.aupdate_state(config, {
                            "messages": [("user", feedback)],
                            "is_approved": False
                        })
                        print_step("Resuming workflow (Back to Agent)...")
                        await graph.ainvoke(None, config)
                        
                    elif choice.lower() in ["q", "quit", "exit"]:
                        print("[SYSTEM]: Exiting interactive session.")
                        break
                    else:
                        print("[ERROR]: Invalid choice. Please try again.")
                        continue
                
                else:
                    print(f"\n[SYSTEM]: Paused at node: {snapshot.next}")
                    print("Resuming...")
                    await graph.ainvoke(None, config)

            else:
                # Finished or Interviewer question
                messages = snapshot.values.get("messages", [])
                last_msg = messages[-1] if messages else None
                content = str(last_msg.content) if last_msg else ""
                
                if "Success" in content or "saved" in content.lower() or "submitted" in content.lower():
                     print_header("WORKFLOW COMPLETED")
                     print(f"[FINAL MESSAGE]: {content}")
                     print(f"[FINAL DATA]: {snapshot.values.get('extracted_data')}")
                     break
                
                if "Error" in content and "Backend" in content:
                     print_error("Backend returned an error.")
                     print(f"[DETAILS]: {content}")
                     print("\n[SYSTEM]: You can try to provide corrected data.")
                
                print_agent_msg(content)
                
                user_reply = await ainput("\n>>> ")
                if user_reply.lower() in ["q", "quit", "exit"]:
                     print("[SYSTEM]: Exiting.")
                     break
                
                print_step("Sending reply to Agent...")
                await graph.ainvoke({"messages": [("user", user_reply)]}, config)


if __name__ == "__main__":
    try:
        asyncio.run(run_interactive())
    except KeyboardInterrupt:
        print("\n\n[SYSTEM]: Test script interrupted by user.")