import yaml
import streamlit as st
import pandas as pd
import csv
import re
import extra_streamlit_components as stx
from rapidfuzz import process, fuzz

def load_config(file_path="use_cases.yaml"):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)

def save_config(data, file_path="use_cases.yaml"):
    with open(file_path, "w") as file:
        yaml.safe_dump(data, file, allow_unicode=True)

def validate_words(input_string):
    """Preveri, da je vnos seznam besed, ločenih z vejicami, ki dovoljuje posebne znake in številke."""
    words = input_string.split(',')
    if all(word.strip() for word in words):  # Preveri, da vsaka beseda ni prazna
        return [word.strip() for word in words]
    else:
        return None        

config = load_config()


tabs = [
    stx.TabBarItemData(id="tab1", title="1. Urejanje nastavitev", description=""),
    stx.TabBarItemData(id="tab2", title="2. Dodaj nov usecase", description=""),
    stx.TabBarItemData(id="tab3", title="3. Izbriši usecase", description=""),
]

# Create the TabBar with the first tab selected by default
selected_tab = stx.tab_bar(data=tabs, default="tab1")
if selected_tab == "tab1":
    st.title("Urejanje nastavitev za use case")

    # Select the use case
    use_case = st.selectbox("Izberi Use Case", list(config["use_cases"].keys()))
    if use_case:
        st.write(f"Urejam nastavitve za use case: **{use_case}**")

        current_config = config["use_cases"][use_case]
        if 'use_case_name' not in st.session_state or st.session_state['use_case_name']!=use_case:
            st.session_state['current_config'] = current_config
            st.session_state['use_case_name'] = use_case
        # st.write(st.session_state['current_config'])
        # st.write(st.session_state['current_config']["mergers"])
        updated_recomenders = st.text_area(
            "Priporočene vrednosti (ločene z vejico):", 
            current_config["recomenders"]
        )

        selected_words = validate_words(current_config["recomenders"])

        if selected_words:
            not_in_any = [word for word in selected_words if word not in st.session_state['current_config']["mergers"] and word not in st.session_state['current_config']["renamers"] and word not in st.session_state['current_config']["identificators"]]
            if not_in_any:
                st.write("Besede, ki niso v pravilih združevanja, preimenovanja ali identifikatorjih:")
                for word in not_in_any:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.write(word)
                    with col2:
                        if st.button(f"Dodaj v združevanje", key=f"add_merger_{word}"):
                            st.session_state['current_config']["mergers"][word] = word
                            st.rerun()
                    with col3:
                        if st.button(f"Dodaj v preimenovanje", key=f"add_renamer_{word}"):
                            st.session_state['current_config']["renamers"][word] = word
                            st.rerun()
                    with col4:
                        if st.button(f"Dodaj v identifikatorje", key=f"add_identifier_{word}"):

                            valid_identifiers = {k: v for k, v in st.session_state['current_config']["identificators"].items() if k not in ["drugo", "ne vem", "neznano"]}
                            if valid_identifiers:
                                new_identifier = str(max(int(value) for value in valid_identifiers.values()) + 1)
                            else:
                                new_identifier = "1"
                            st.session_state['current_config']["identificators"][word] = new_identifier
                            st.rerun()   

        # Editable Sections
        updated_mergers_df = pd.DataFrame(
            list(st.session_state['current_config']["mergers"].items()), 
            columns=["Izvirno ime", "Novo ime"],
        )
        st.subheader("Pravila za združevanje rezultatov:")
        updated_mergers = st.data_editor(
            updated_mergers_df,
            num_rows="dynamic",  
            use_container_width=True,  
            key="updated_mergers"      
        )
        updated_renamers_df = pd.DataFrame(
            list(st.session_state['current_config']["renamers"].items()), 
            columns=["Izvirno ime", "Novo ime"]
        )
        st.subheader("Pravila za preimenovanje rezultatov:")
        updated_renamers = st.data_editor(
            updated_renamers_df,
            num_rows="dynamic",  
            use_container_width=True, 
            key="updated_renamers"       
        )
        updated_identificators_df = pd.DataFrame(
            list(st.session_state['current_config']["identificators"].items()), 
            columns=["Ime", "Identifikator"]
        )
        st.subheader("Identificators:")
        updated_identificators = st.data_editor(
            updated_identificators_df,
            num_rows="dynamic",  
            use_container_width=True,    
            key="updated_identificators"    
        )


        updated_columns = st.text_area(
            "Predvidena polja (ločene z vejico):", 
            current_config["columns"]
        )
     
        
        # Save Changes
        if st.button("Shrani spremembe"):
            try:
                # Update the configuration with user inputs
                current_config["mergers"] = dict(updated_mergers.values)
                current_config["renamers"] = dict(updated_renamers.values)
                current_config["identificators"] = dict(updated_identificators.values)
                current_config["columns"] = updated_columns
                current_config["recomenders"] = updated_recomenders

                # Save to file
                save_config(config)
                st.success("Konfiguracija shranjena!")
            except Exception as e:
                st.error(f"Napaka pri shranjevanju konfiguracije: {e}")

if selected_tab == "tab2":
    st.title("Dodaj use case")                

    # Input for new use case name
    new_use_case_name = st.text_input("Ime novega use case-a")

    st.write("Naloži CSV datoteko in izberi stolpce.")
    # File uploader
    uploaded_file = st.file_uploader("Naloži CSV", type="csv")

    recognised_column_names = []
    processed_dfs = []
    word_input = None

    if uploaded_file:
        
        have_delimiter = False
        try:
            uploaded_file.seek(0)  
            sample = uploaded_file.read(1024).decode('utf-8')  
            uploaded_file.seek(0)  
            detected_delimiter = csv.Sniffer().sniff(sample).delimiter 
            have_delimiter = True
        except csv.Error:
            detected_delimiter = ';'
            have_delimiter = True
        except Exception as e:
            st.error(f"Prišlo je do napake pri branju datoteke: {e}")    
        if have_delimiter == True:      
            try:

                df = pd.read_csv(uploaded_file, delimiter=detected_delimiter)
                unique_words_set = set() 

                # Input for column name
                selected_columns = st.multiselect(
                    "Izberite stolpce, ki bodo pred izbrani:",
                    options=df.columns.tolist(),
                )
                if len(selected_columns) > 0:
                    columns = ','.join(selected_columns)
                    column_names = [col.strip() for col in columns.split(',')]
                    for col in column_names:
                        if col in df.columns:
                            recognised_column_names.append(col)
                            unique_words = df[col].dropna().unique()
                            # Strip words, filter out empty stfrings, and add unique words to the set
                            unique_words_set.update([str(word).strip() for word in unique_words if str(word).strip()])
                        else:
                            st.error(f"Stolpec '{col}' ni najden v naloženi CSV datoteki.")

                    # Convert the unique set back to a sorted string for display
                    unique_words_text = ", ".join(sorted(unique_words_set))

                    # Display the unique words
                    st.write("Unikatne besede:")
                    unique_words_area = st.text_area(
                        "Unikatne besede v stolpcih:",
                        value=unique_words_text,
                        height=150,
                        label_visibility="collapsed"
                    )   
                    if len(recognised_column_names) > 0:
        
                        def normalize(word):
                            return re.sub(r"[^a-z0-9\sščž]", "", word.lower())

                        unique_words_list = [normalize(word.strip()) for word in unique_words_area.split(",")]


                        recommended_list = []


                        for word in unique_words_list:
                            # Check if the word matches an existing recommended word
                            if recommended_list:
                                match_result = process.extractOne(word, recommended_list, scorer=fuzz.ratio)
                                match = match_result[0] if match_result else None
                                score = match_result[1] if match_result else 0
                            else:
                                match, score = None, 0

                            # If no close match is found, add it to the recommended list
                            if score < 85:  
                                recommended_list.append(word)
                        st.write("Priporočen seznam besed:")
                        recomenders = st.text_area(
                            "Priporočene besede:",
                            value=", ".join(recommended_list),
                            height=150,
                            label_visibility="collapsed"
                        )


                        st.subheader("Pravila za združevanje rezultatov:")
                        new_mergers_df = pd.DataFrame(columns=["Izvirno ime", "Novo ime"])
                        new_mergers = st.data_editor(
                            new_mergers_df,
                            num_rows="dynamic",
                            use_container_width=True,
                            key="new_mergers"
                        )

                        st.subheader("Pravila za preimenovanje rezultatov:")
                        new_renamers_df = pd.DataFrame(columns=["Izvirno ime", "Novo ime"])
                        new_renamers = st.data_editor(
                            new_renamers_df,
                            num_rows="dynamic",
                            use_container_width=True,
                            key="new_renamers"
                        )

                        st.subheader("Identificators:")
                        new_identificators_df = pd.DataFrame(
                            [
                                ["drugo", "98"],
                                ["ne vem", "99"],
                                ["neznano", "100"]
                            ],
                            columns=["Ime", "Identifikator"]
                        )
                        new_identificators = st.data_editor(
                            new_identificators_df,
                            num_rows="dynamic",
                            use_container_width=True,
                            key="new_identificators"
                        )


                        if st.button("Dodaj use case"):
                            if new_use_case_name:
                                if new_use_case_name not in config["use_cases"]:
                                    config["use_cases"][new_use_case_name] = {
                                        "mergers": dict(new_mergers.values),
                                        "renamers": dict(new_renamers.values),
                                        "identificators": dict(new_identificators.values),
                                        "columns": columns,
                                        "recomenders": recomenders
                                    }
                                    save_config(config)
                                    st.success(f"Use case '{new_use_case_name}' uspešno dodan!")
                                else:
                                    st.error(f"Use case '{new_use_case_name}' že obstaja.")
                            else:
                                st.error("Ime use case-a ne sme biti prazno.")


                    else:
                        st.error(f"Stolpci ne obstajajo v naloženi CSV datoteki.")
            except pd.errors.EmptyDataError:
                st.error("CSV datoteka je prazna ali ima napačno obliko.")
            except csv.Error:
                st.error("Ni mogoče zaznati ločila v datoteki. Preverite, ali je datoteka pravilno oblikovana." )
            except Exception as e:
                st.error(f"Prišlo je do napake pri branju datoteke: {e}")

if selected_tab == "tab3":
    st.title("Izbriši use case")    
    # Select the use case to delete
    use_case_to_delete = st.selectbox("Izberi Use Case za izbris", list(config["use_cases"].keys()))
    
    if st.button("Izbriši izbrani use case"):
        if use_case_to_delete:
            try:
                # Remove the selected use case from the configuration
                del config["use_cases"][use_case_to_delete]
                
                # Save the updated configuration to the file
                save_config(config)
                
                st.success(f"Use case '{use_case_to_delete}' uspešno izbrisan!")
            except Exception as e:
                st.error(f"Napaka pri brisanju use case-a: {e}")
        else:
            st.error("Izberi use case za izbris.")