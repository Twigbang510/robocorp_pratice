from robocorp.tasks import task
import time, os
from DOP.RPA.ProcessArgument import ProcessArgument
from DOP.RPA.Asset import Asset
from DOP.RPA.Log import Log

assets = Asset()
arg_process = ProcessArgument()

@task
def test_dop():
    # print("arg", arg_process.get_in_arg('demo'))
    print(f"My Asset: {assets.get_asset('lyrics_user').get('value')['username']}")
    