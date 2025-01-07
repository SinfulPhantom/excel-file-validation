import pytest
from flask import url_for
import pandas as pd
from app.modules.app_status import AppStatusService
from app.models.data_models import EnvDataModel

def test_index_page(client):
    """Test the index page loads and contains links to both tools"""
    response = client.get(url_for('main.index'))
    assert response.status_code == 200
    
    # Check for both tool links
    assert b'Excel Validation' in response.data
    assert b'App Status' in response.data
    assert url_for('main.excel_validation') in response.data.decode()
    assert url_for('main.app_status') in response.data.decode()

def test_app_status_page(client):
    """Test the app status page loads with the correct form"""
    response = client.get(url_for('main.app_status'))
    assert response.status_code == 200
    
    # Check for form elements
    content = response.data.decode()
    assert 'App File (CSV)' in content
    assert 'Workload File (CSV)' in content
    assert 'name="app_file"' in content
    assert 'name="workload_file"' in content

def test_app_status_service():
    """Test the AppStatusService functionality"""
    service = AppStatusService()
    
    # Create test data
    app_data = {
        'App': ['Test App 1', 'Test App 2']
    }
    app_df = pd.DataFrame(app_data)
    
    wkld_data = {
        'label:app': ['TestApp1', 'TestApp1', 'TestApp2'],
        'label:env': ['E-Production', 'E-Development', 'E-Production'],
        'agent_status': [None, None, 'active'],
        'enforcement_mode': ['full', 'full', 'monitor']
    }
    wkld_df = pd.DataFrame(wkld_data)
    
    # Process the data
    service.process_applications(app_df, wkld_df)
    
    # Check if output file was created
    import os
    from app.utils.constants import OUTPUT_FILE
    assert os.path.exists(OUTPUT_FILE)
    
    # Clean up
    os.remove(OUTPUT_FILE)

def test_env_data_model():
    """Test the EnvDataModel data validation"""
    # Test with minimal data
    model = EnvDataModel(assigned_app="Test App", app_label="TestApp")
    assert model.assigned_app == "Test App"
    assert model.app_label == "TestApp"
    assert model.npe_fe_count == "0 / 0 Enforced"
    assert model.prod_fe_count == "0 / 0 Enforced"
    
    # Test with full data
    full_data = {
        "assigned_app": "Test App",
        "app_label": "TestApp",
        "npe_fe_count": "1 / 2 Enforced",
        "prod_fe_count": "2 / 2 Enforced",
        "npe_managed": 1,
        "npe_unmanaged": 1,
        "npe_total": 2,
        "prod_managed": 2,
        "prod_unmanaged": 0,
        "prod_total": 2
    }
    model = EnvDataModel(**full_data)
    for key, value in full_data.items():
        assert getattr(model, key) == value

def test_app_status_form_submission(client):
    """Test form submission with files"""
    # Create test CSV files
    app_csv = "App\nTest App 1\nTest App 2"
    wkld_csv = "label:app,label:env,agent_status,enforcement_mode\n" \
               "TestApp1,E-Production,,full\n" \
               "TestApp1,E-Development,,full\n" \
               "TestApp2,E-Production,active,monitor"
    
    # Create test files
    import io
    app_file = (io.BytesIO(app_csv.encode()), 'app.csv')
    wkld_file = (io.BytesIO(wkld_csv.encode()), 'workload.csv')
    
    data = {
        'app_file': app_file,
        'workload_file': wkld_file
    }
    
    response = client.post(
        url_for('main.app_status'),
        data=data,
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 200
    assert b'Report Generated Successfully!' in response.data
