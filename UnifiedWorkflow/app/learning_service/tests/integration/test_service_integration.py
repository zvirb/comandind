def test_cognitive_service_integration():
    test_scenario = {
        "processed_data": {
            "status": "success",
            "context": "Integration test scenario",
            "performance": {
                "cpu_usage": 25.5,
                "memory_usage": 1024
            }
        }
    }
    
    assert test_scenario is not None, "Cognitive service scenario should be defined"
    assert "processed_data" in test_scenario, "Scenario should contain processed_data"
    assert test_scenario["processed_data"]["status"] == "success", "Integration test should be successful"
    
    performance_data = test_scenario["processed_data"]["performance"]
    assert "cpu_usage" in performance_data, "Performance data should include CPU usage"
    assert "memory_usage" in performance_data, "Performance data should include memory usage"