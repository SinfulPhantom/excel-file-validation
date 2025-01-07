from pydantic import BaseModel
from typing import List, Dict
from pandas import DataFrame
import pandas as pd
import sys, os, wx

pd.options.mode.chained_assignment = None

# Constants
CSV_FORMAT: str = '*.csv'
INPUT_DIALOG: str = 'Choose App File'
WORKLOAD_DIALOG: str = 'Choose Workloader File'
OUTPUT_FILE: str = 'App_Status.csv'
NPE_ENVS: List[str] = [
    'E-Development', 'E-DIT', 'E-PLAB', 'E-QAT', 'E-sandbox', 
    'E-Temporary', 'E-Training', 'E-UAT', 'E-Testing', 'E-test'
]
PROD_ENVS: List[str] = ['E-Administrative', 'E-Production', 'E-Staging']
BUNDLED_ENVS: Dict[str, List[str]] = {'npe': NPE_ENVS, 'prod': PROD_ENVS}
OUTPUT_HEADERS: List[str] = [
    'Assigned Apps', 'App Label', 'NPE FE','PROD FE','NPE Managed', 'NPE Unmanaged', 'NPE_Total',
    'Prod Managed', 'Prod Unmanaged', 'Prod_Total'
]

# Data Model
class EnvDataModel(BaseModel):
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


def process_applications():
    """
    Based on the Application CSV, we are going to look for matching app names
    and process them with the workload file.
    """
    output_data: List[EnvDataModel] = []  # List of compiled data for the export file

    for _, app_row in app_df.iterrows():
        assigned_app: str = app_row[0]  # Column 0 in app.csv (index-based)
        normalized_name: str = assigned_app.replace(' ', '')

        # Find matching app_label in wkld_df
        matched_rows: DataFrame = wkld_df.loc[wkld_df['label:app'] == normalized_name]

        if matched_rows.empty:
            print(f'No match found for: {assigned_app}')
            output_data.append(EnvDataModel(assigned_app=assigned_app, app_label="No Match Found"))
        else:
            app_workloads: EnvDataModel = process_workloaders(assigned_app, normalized_name, matched_rows)
            output_data.append(app_workloads)

        # Now that we've populated the output_data, we can export the app status analysis
        create_export(output_data)

def process_workloaders(app_name: str, wkld_name: str, app_data: DataFrame) -> EnvDataModel:
    """
    Creating our data model with aggregated data and formatted fe_counts

    Args:
        app_name (str): Application Name
        wkld_name (str): Name of the original unformatted app name
        app_data (DataFrame): All row data for specific application

    Returns:
        EnvDataModel: Compiled data for necessary export columns
    """
    # Create environment type column
    env_data: DataFrame = app_data.assign(
        env_type=lambda x: x['label:env'].apply(
            lambda e: 'prod' if e in Bundled_ENVS['prod'] 
            else 'npe' if e in Bundled_ENVS['npe'] 
            else 'unknown'
        ),
        is_managed=lambda x: x['agent_status'].isna(),
        is_full=lambda x: x['enforcement_mode'].str.contains('full', case=False),
    )

    # Group and aggregate data
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

    # NPE and PROD stats
    npe_stats: Dict = stats['npe']
    prod_stats: Dict = stats['prod']

    # Create our data model
    return EnvDataModel(
        assigned_app=app_name,
        app_label=f'A-{wkld_name}',
        npe_fe_count=npe_stats['fe_count'],
        prod_fe_count=prod_stats['fe_count'],
        npe_managed=npe_stats['managed'],
        npe_unmanaged=npe_stats['unmanaged'],
        npe_total=npe_stats['total'],
        prod_managed=prod_stats['managed'],
        prod_unmanaged=prod_stats['unmanaged'],
        prod_total=prod_stats['total'],
    )

def create_export(data: List[EnvDataModel]) -> None:
    """
    Use the data we've compiled and generate the app status CSV file

    Args:
        data (List[EnvDataModel]): List of compiled data models
    """
    file: str = "App_Status.csv"

    # Remove any existing App_Status.csv file
    if os.path.exists(file):
        os.remove(file)

    try:
        # Build the data
        data_vals: List = [[key[1] for key in row] for row in data]

        # Create the DataFrame and save the file
        output_df: DataFrame = pd.DataFrame(data_vals, columns=OUTPUT_HEADERS).astype(str)
        output_df.to_csv(file, index=False)
        print(f'Exported {file} successfully')
    except Exception as e:
        print(f'Failed to export {file} with error: {e}')

def select_file(window_dialog: str, wildcard: str = '*.csv') -> str:
    """
    Opens a file dialog and returns the selected file path

    Args:
        window_dialog (str): The title of the file dialog
        wildcard (str, optional): The file type filter. Defaults to '*.csv'.

    Returns:
        str: The selected filepath
    """
    _ = wx.App(None)    # Necessary for file dialog
    dialog = wxFileDialog(
        None,
        window_dialog,
        wildcard=wildcard,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
    )
    if dialog.ShowModal() == wx.ID_OK:
        return dialog.GetPath()
    else:
        path = None
    
    dialog.Destroy()    # Close the file dialog
    return path

def format_app_name(app_name: str) -> str:
    """
    Format the app name to remove the 'A-' prefix

    Args:
        app_name (str): The app name

    Returns:
        str: The formatted app name
    """
    if pd.isna(app_name):
        return app_name
    if app_name.startswith('A-SA-'):
        return app_name[2:]
    return app_name.replace('A-','')


if __name__ == '__main__':
    app_file: str = ''
    wkld_file: str = ''

    if len(sys.argv) > 1:
        # Check if User is attempting to use test mode
        # This can be done with appending --test to the run command
        # e.g. python appstatus.py --test
        if sys.argv[1] == '--test':
            app_file = 'app.csv'
            wkld_file = 'wkld.csv'
    else:
        # Prompt the user for app and workload files
        app_file = select_file(INPUT_DIALOG)
        wkld_file = select_file(WORKLOAD_DIALOG)

    app_df: DataFrame = pd.read_csv(app_file, header=None)
    wkld_df: DataFrame = pd.read_csv(wkld_file)

    # Modify and apply the proper naming conventions for Application names
    wkld_df['label:app'] = wkld_df['label:app'].apply(format_app_name)

    # Begin processing each application
    process_applications()