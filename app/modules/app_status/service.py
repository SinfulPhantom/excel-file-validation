from typing import List, Dict
import pandas as pd
from app.models.data_models import EnvDataModel
from app.utils.constants import (
    BUNDLED_ENVS, OUTPUT_HEADERS, OUTPUT_FILE
)

class AppStatusService:
    def __init__(self):
        pd.options.mode.chained_assignment = None
        
    def process_applications(self, app_df: pd.DataFrame, wkld_df: pd.DataFrame) -> None:
        """
        Process applications and generate status report
        
        Args:
            app_df (pd.DataFrame): Application data
            wkld_df (pd.DataFrame): Workload data
        """
        output_data: List[EnvDataModel] = []

        for _, app_row in app_df.iterrows():
            assigned_app: str = app_row[0]
            normalized_name: str = assigned_app.replace(' ', '')

            # Find matching app_label in wkld_df
            matched_rows: pd.DataFrame = wkld_df.loc[wkld_df['label:app'] == normalized_name]

            if matched_rows.empty:
                print(f'No match found for: {assigned_app}')
                output_data.append(EnvDataModel(assigned_app=assigned_app, app_label="No Match Found"))
            else:
                app_workloads: EnvDataModel = self._process_workloaders(assigned_app, normalized_name, matched_rows)
                output_data.append(app_workloads)

        self._create_export(output_data)

    def _process_workloaders(self, app_name: str, wkld_name: str, app_data: pd.DataFrame) -> EnvDataModel:
        """
        Process workloader data for a specific application
        
        Args:
            app_name (str): Application name
            wkld_name (str): Workload name
            app_data (pd.DataFrame): Application data
            
        Returns:
            EnvDataModel: Processed environment data
        """
        env_data: pd.DataFrame = app_data.assign(
            env_type=lambda x: x['label:env'].apply(
                lambda e: 'prod' if e in BUNDLED_ENVS['prod']
                else 'npe' if e in BUNDLED_ENVS['npe']
                else 'unknown'
            ),
            is_managed=lambda x: x['agent_status'].isna(),
            is_full=lambda x: x['enforcement_mode'].str.contains('full', case=False),
        )

        stats: Dict = (
            env_data.groupby('env_type')
            .agg(
                managed=('is_managed', 'sum'),
                unmanaged=('is_managed', lambda x: (~x).sum()),
                total=('env_type', 'size'),
                fe_count=('is_full', lambda x: f"{x.sum()} / {x.count()} Enforced")
            )
            .to_dict('index')
        )

        npe_stats: Dict = stats.get('npe', {})
        prod_stats: Dict = stats.get('prod', {})

        return EnvDataModel(
            assigned_app=app_name,
            app_label=wkld_name,
            npe_fe_count=npe_stats.get('fe_count', "0 / 0 Enforced"),
            prod_fe_count=prod_stats.get('fe_count', "0 / 0 Enforced"),
            npe_managed=npe_stats.get('managed', 0),
            npe_unmanaged=npe_stats.get('unmanaged', 0),
            npe_total=npe_stats.get('total', 0),
            prod_managed=prod_stats.get('managed', 0),
            prod_unmanaged=prod_stats.get('unmanaged', 0),
            prod_total=prod_stats.get('total', 0)
        )

    def _create_export(self, data: List[EnvDataModel]) -> None:
        """
        Create export file with processed data
        
        Args:
            data (List[EnvDataModel]): List of processed environment data
        """
        export_data = []
        for item in data:
            export_data.append({
                'Assigned Apps': item.assigned_app,
                'App Label': item.app_label,
                'NPE FE': item.npe_fe_count,
                'PROD FE': item.prod_fe_count,
                'NPE Managed': item.npe_managed,
                'NPE Unmanaged': item.npe_unmanaged,
                'NPE_Total': item.npe_total,
                'Prod Managed': item.prod_managed,
                'Prod Unmanaged': item.prod_unmanaged,
                'Prod_Total': item.prod_total
            })

        df = pd.DataFrame(export_data, columns=OUTPUT_HEADERS)
        df.to_csv(OUTPUT_FILE, index=False)
