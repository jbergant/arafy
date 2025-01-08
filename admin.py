import yaml
import streamlit as st
import pandas as pd

def load_config(file_path="use_cases.yaml"):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)

def save_config(data, file_path="use_cases.yaml"):
    with open(file_path, "w") as file:
        yaml.safe_dump(data, file, allow_unicode=True)

config = load_config()

st.title("Admin Configuration Panel")

# Select the use case
use_case = st.selectbox("Select Use Case", list(config["use_cases"].keys()))
if use_case:
    st.write(f"Editing Configuration for: **{use_case}**")
    current_config = config["use_cases"][use_case]
    
    # Editable Sections
    updated_mergers = st.text_area(
        "Mergers (key-value pairs in YAML format):", 
        yaml.safe_dump(current_config["mergers"], allow_unicode=True)
    )
    updated_renamers = st.text_area(
        "Renamers (key-value pairs in YAML format):", 
        yaml.safe_dump(current_config["renamers"], allow_unicode=True)
    )
    updated_identificators = st.text_area(
        "Identificators (key-value pairs in YAML format):", 
        yaml.safe_dump(current_config["identificators"], allow_unicode=True)
    )
    updated_columns = st.text_area(
        "Columns (comma-separated values):", 
        current_config["columns"]
    )
    updated_recomenders = st.text_area(
        "Recomenders (comma-separated values):", 
        current_config["recomenders"]
    )
    
    # Save Changes
    if st.button("Save Changes"):
        try:
            # Update the configuration with user inputs
            current_config["mergers"] = yaml.safe_load(updated_mergers)
            current_config["renamers"] = yaml.safe_load(updated_renamers)
            current_config["identificators"] = yaml.safe_load(updated_identificators)
            current_config["columns"] = updated_columns
            current_config["recomenders"] = updated_recomenders

            # Save to file
            save_config(config)
            st.success("Configuration saved successfully!")
        except Exception as e:
            st.error(f"Error saving configuration: {e}")