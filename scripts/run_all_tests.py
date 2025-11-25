"""
Run all tests for Sport Agent MVP
No special characters in code
"""
import asyncio
import sys
import os
import subprocess
import time

sys.path.append(os.getcwd())


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


async def check_api_server():
    """Check if API server is running"""
    import httpx
    
    print_section("TEST 0: Check API Server")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8080/health",
                timeout=5.0
            )
            if response.status_code == 200:
                print("API Server is running")
                print(f"Response: {response.json()}")
                return True
            else:
                print(f"API Server returned status code: {response.status_code}")
                return False
    except Exception as e:
        print(f"API Server is NOT running: {e}")
        print("\nPlease start the server with:")
        print("uvicorn src.services.api.main:app --reload --port 8080")
        return False


async def test_data_pipeline():
    """Test data pipeline"""
    print_section("TEST 1: Data Pipeline")
    
    try:
        from src.data_pipeline.entity_resolver import entity_resolver
        
        # Test entity resolution
        await entity_resolver.initialize()
        
        test_cases = [
            ("Manchester United FC", "exact match"),
            ("Manchester United", "no suffix"),
            ("Man United", "alias"),
            ("Liverpool", "english"),
        ]
        
        print("Testing Entity Resolver:")
        for team_name, test_type in test_cases:
            result = await entity_resolver.resolve_team(team_name)
            status = "PASS" if result else "FAIL"
            print(f"  [{status}] {test_type}: '{team_name}' -> {result}")
        
        print("\nData Pipeline Test: COMPLETED")
        return True
        
    except Exception as e:
        print(f"Data Pipeline Test: FAILED - {e}")
        return False


async def test_agent_v1():
    """Test Agent V1 endpoint"""
    print_section("TEST 2: Agent V1 Endpoint")
    
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8080/api/v1/agent/query",
                json={"query": "Man United"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                print("V1 Response received successfully")
                print(f"Planner Version: {data.get('planner_version')}")
                print(f"Plan Steps: {len(data.get('plan_steps', []))} steps")
                print(f"Answer length: {len(data.get('answer', ''))} chars")
                return True
            else:
                print(f"V1 Test FAILED: HTTP {response.status_code}")
                return False
                
    except Exception as e:
        print(f"V1 Test FAILED: {e}")
        return False


async def test_agent_v2():
    """Test Agent V2 endpoint"""
    print_section("TEST 3: Agent V2 Endpoint")
    
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8080/api/v1/agent/query/v2",
                json={"query": "Analyze Man United performance"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                print("V2 Response received successfully")
                print(f"Planner Version: {data.get('planner_version')}")
                print(f"Plan Steps: {len(data.get('plan_steps', []))} steps")
                
                # Check tool traces
                traces = data.get('tool_traces', [])
                print(f"\nTool Execution Details:")
                for i, trace in enumerate(traces, 1):
                    print(f"  {i}. {trace['tool_name']}")
                    print(f"     Latency: {trace['latency_ms']}ms")
                
                return True
            else:
                print(f"V2 Test FAILED: HTTP {response.status_code}")
                return False
                
    except Exception as e:
        print(f"V2 Test FAILED: {e}")
        return False


async def test_stats_tool():
    """Test StatsTool directly"""
    print_section("TEST 4: StatsTool Direct Call")
    
    try:
        from src.agent.tools.stats_tool import stats_tool
        
        result = await stats_tool.get_team_stats(
            team_name="Manchester United",
            last_n=10
        )
        
        if "MUN" in result or "Manchester United" in result:
            print("StatsTool returned data successfully")
            print("\nSample output:")
            lines = result.split('\n')
            for line in lines[:10]:
                print(line)
            if len(lines) > 10:
                print("...")
            return True
        else:
            print(f"StatsTool FAILED: Unexpected output")
            print(f"Got: {result[:200]}")
            return False
            
    except Exception as e:
        print(f"StatsTool Test FAILED: {e}")
        return False


async def test_match_tool():
    """Test MatchTool directly"""
    print_section("TEST 5: MatchTool Direct Call")
    
    try:
        from src.agent.tools.match_tool import match_tool
        
        result = await match_tool.get_recent_matches(
            team_name="Manchester United",
            limit=5
        )
        
        if "MUN" in result or "Manchester United" in result:
            print("MatchTool returned data successfully")
            print("\nSample output:")
            lines = result.split('\n')
            for line in lines[:8]:
                print(line)
            return True
        else:
            print(f"MatchTool FAILED: Unexpected output")
            print(f"Got: {result[:200]}")
            return False
            
    except Exception as e:
        print(f"MatchTool Test FAILED: {e}")
        return False


async def test_database_connection():
    """Test database connection"""
    print_section("TEST 6: Database Connection")
    
    try:
        from sqlalchemy import select, func
        from src.infra.db.session import AsyncSessionLocal
        from src.infra.db.models import Match, Team
        
        async with AsyncSessionLocal() as db:
            # Count teams
            stmt = select(func.count(Team.team_id))
            result = await db.execute(stmt)
            team_count = result.scalar()
            
            # Count matches
            stmt = select(func.count(Match.match_id))
            result = await db.execute(stmt)
            match_count = result.scalar()
            
            print(f"Database connection: SUCCESS")
            print(f"Teams in database: {team_count}")
            print(f"Matches in database: {match_count}")
            
            if team_count > 0 and match_count > 0:
                return True
            else:
                print("WARNING: Database has no data. Run seed_db.py")
                return False
                
    except Exception as e:
        print(f"Database Test FAILED: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n")
    print("=" * 60)
    print("  Sport Agent MVP - Complete Test Suite")
    print("=" * 60)
    
    start_time = time.time()
    
    # Track results
    results = {}
    
    # Test 0: Check API Server
    results['api_server'] = await check_api_server()
    
    if not results['api_server']:
        print("\n" + "!" * 60)
        print("  API Server is not running!")
        print("  Please start it before running tests.")
        print("!" * 60)
        return
    
    # Test 1: Data Pipeline
    results['data_pipeline'] = await test_data_pipeline()
    
    # Test 2: Agent V1
    results['agent_v1'] = await test_agent_v1()
    
    # Test 3: Agent V2
    results['agent_v2'] = await test_agent_v2()
    
    # Test 4: StatsTool
    results['stats_tool'] = await test_stats_tool()
    
    # Test 5: MatchTool
    results['match_tool'] = await test_match_tool()
    
    # Test 6: Database
    results['database'] = await test_database_connection()
    
    # Summary
    duration = time.time() - start_time
    
    print_section("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"Tests Run: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Duration: {duration:.2f} seconds")
    print("\nDetailed Results:")
    
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {test_name}")
    
    print("\n" + "=" * 60)
    if passed == total:
        print("  ALL TESTS PASSED!")
    else:
        print(f"  WARNING: {total - passed} TEST(S) FAILED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

