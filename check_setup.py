import asyncio
from spade import agent

class TestAgent(agent.Agent):
    async def setup(self):
        print("Agent is running!")

async def main():
    print("Starting test agent...")
    test_agent = TestAgent("client_manager@localhost", "password")
    await test_agent.start()
    print("Agent started successfully!")
    await asyncio.sleep(5)
    await test_agent.stop()
    print("Agent stopped.")

if __name__ == "__main__":
    asyncio.run(main())