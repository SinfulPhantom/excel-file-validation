from pydantic import BaseModel
from typing import List, Dict

class EnvDataModel(BaseModel):
    """
    Data model for environment status information
    """
    assigned_app: str
    app_label: str
    npe_fe_count: str = "0 / 0 Enforced"
    prod_fe_count: str = "0 / 0 Enforced"
    npe_managed: int = 0
    npe_unmanaged: int = 0
    npe_total: int = 0
    prod_managed: int = 0
    prod_unmanaged: int = 0
    prod_total: int = 0
