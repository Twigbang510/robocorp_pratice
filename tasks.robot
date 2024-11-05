*** Settings ***
Library           tasks.py
Library           DOP.RPA.ProcessArgument
Library           DOP.RPA.Asset

*** Variables ***

*** Tasks ***
Run All Tasks
    Run Main Tasks  

*** Keywords ***
Run Main Tasks
    ${username}=    Get In Arg    username
    ${username_value}=    Set Variable    ${username}[value]
    ${password}=    Get In Arg    password
    ${password_value}=    Set Variable    ${password}[value]
    ${song_name}=    Get In Arg    song_name
    ${song_name_value}=    Set Variable    ${song_name}[value]
    
    Run Main    ${username_value}    ${password_value}    ${song_name_value}



