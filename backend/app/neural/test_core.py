"""
Brain 3.0 - Test Script
========================

Testet die Neural Core Integration
"""

import asyncio
import json

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "postgresql+asyncpg://brain:brain@localhost:5432/brain"


async def test_neural_core():
    """Testet die Neural Core Funktionalität"""
    
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Import NeuralCore
        from app.neural.core import NeuralCore, ExecutionRequest
        
        core = NeuralCore(db)
        
        print("\n" + "="*60)
        print("🧠 BRAIN 3.0 - TEST SUITE")
        print("="*60)
        
        # Test 1: Parameter holen
        print("\n📊 Test 1: Parameter holen")
        params = await core.get_all_parameters()
        print(f"   Gefundene Parameter: {len(params)}")
        for key, value in params.items():
            print(f"   - {key}: {value}")
        
        # Test 2: Parameter setzen
        print("\n✏️  Test 2: Parameter setzen")
        old_creativity = await core.get_parameter("creativity")
        await core.set_parameter("creativity", 0.9)
        new_creativity = await core.get_parameter("creativity")
        print(f"   creativity: {old_creativity} → {new_creativity}")
        
        # Zurücksetzen
        await core.set_parameter("creativity", old_creativity)
        
        # Test 3: States holen
        print("\n🎭 Test 3: States")
        states = ["default", "creative", "fast", "safe"]
        for state_name in states:
            state = await core.get_state(state_name)
            if state:
                print(f"   - {state_name}: {state['parameters']}")
        
        # Test 4: Synapsen auflisten
        print("\n🔗 Test 4: Synapsen")
        synapses = await core.list_synapses()
        print(f"   Gefundene Synapsen: {len(synapses)}")
        for s in synapses:
            print(f"   - {s.synapse_id}: {s.target_module}.{s.capability}")
        
        # Test 5: Execution
        print("\n🚀 Test 5: Execution")
        result = await core.execute(ExecutionRequest(
            action="skill_execute",
            payload={"skill_key": "test_skill"}
        ))
        print(f"   Erfolg: {result.success}")
        print(f"   Synapse: {result.synapse_id}")
        print(f"   Zeit: {result.execution_time_ms:.2f}ms")
        
        # Test 6: Stats
        print("\n📈 Test 6: Stats")
        stats = await core.get_synapse_stats(hours=1)
        print(f"   Executions in last hour: {len(stats)}")
        
        print("\n" + "="*60)
        print("✅ ALLE TESTS ABGESCHLOSSEN")
        print("="*60)


async def test_api_endpoints():
    """Testet die API Endpoints"""
    
    import httpx
    
    base_url = "http://localhost:8000"
    
    print("\n" + "="*60)
    print("🌐 API ENDPOINT TESTS")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        # Health
        print("\n� health Check")
        r = await client.get(f"{base_url}/neural/health")
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")
        
        # Parameters
        print("\n📊 GET /neural/parameters")
        r = await client.get(f"{base_url}/neural/parameters")
        print(f"   Status: {r.status_code}")
        
        # States
        print("\n🎭 GET /neural/states")
        r = await client.get(f"{base_url}/neural/states")
        print(f"   Status: {r.status_code}")
        
        # Synapses
        print("\n🔗 GET /neural/synapses")
        r = await client.get(f"{base_url}/neural/synapses")
        print(f"   Status: {r.status_code}")
        
        # Execute
        print("\n🚀 POST /neural/execute")
        r = await client.post(f"{base_url}/neural/execute", json={
            "action": "skill_execute",
            "payload": {"skill_key": "test"}
        })
        print(f"   Status: {r.status_code}")
        
        # Stats
        print("\n📈 GET /neural/stats")
        r = await client.get(f"{base_url}/neural/stats")
        print(f"   Status: {r.status_code}")


async def main():
    """Main entry point"""
    print("\n🧠 BRAIN 3.0 - TEST SUITE")
    print("="*60)
    
    try:
        await test_neural_core()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
