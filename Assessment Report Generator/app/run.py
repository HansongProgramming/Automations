"""
Local development startup script
"""
import sys
import asyncio

# Set Windows event loop policy before anything else
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("✓ Windows event loop policy configured")

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting server (Development Mode)")
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )