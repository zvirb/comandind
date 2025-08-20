import ollama
import asyncio
import time

async def stream_chat():
    start_time = time.time()
    stream = ollama.chat(
        model='llama3.1:8b',
        messages=[{'role': 'user', 'content': 'Explain async streaming in Python'}],
        stream=True
    )
    
    full_response = ""
    for chunk in stream:
        if 'message' in chunk:
            print(chunk['message']['content'], end='', flush=True)
            full_response += chunk['message']['content']
    
    end_time = time.time()
    print(f"\n\nTotal Response Time: {end_time - start_time:.2f} seconds")
    print(f"Response Length: {len(full_response)} characters")

async def main():
    await stream_chat()

if __name__ == '__main__':
    asyncio.run(main())