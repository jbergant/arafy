import streamlit as st
import pandas as pd
import Levenshtein
import csv
import copy
import logging
import extra_streamlit_components as stx
import yaml


logging.basicConfig(level=logging.INFO)


if 'similarity_threshold' not in st.session_state:
    st.session_state['similarity_threshold'] = 0.7

# Function to log messages
def log_message(message):
    logging.info(message)

def validate_words(input_string):
    """Preveri, da je vnos seznam besed, ločenih z vejicami, ki dovoljuje posebne znake in številke."""
    words = input_string.split(',')
    if all(word.strip() for word in words):  # Preveri, da vsaka beseda ni prazna
        return [word.strip() for word in words]
    else:
        return None

def process_csv(df, column, words):

    # Preveri, ali stolpec obstaja
    if column not in df.columns:
        st.error(f"Stolpec '{column}' ni v naloženi CSV datoteki.")
        return None

    # Izračunaj Levenshteinove razmerje
    def find_best_match(value, reference_names):
        if pd.isna(value) or value.strip() == "":
            return None, None, None
        best_match = None
        highest_similarity = 0
        for name in reference_names:
            similarity = Levenshtein.ratio(value.lower(), name.lower())
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = name

        if highest_similarity > st.session_state['similarity_threshold']:
            return best_match, highest_similarity, False
        else:
            return best_match, highest_similarity, True

    # Uporabi funkcijo na določen stolpec
    df['najboljse_ujemanje'], df['razmerje'], df['za_pregled'] = zip(
        *df[column].astype(str).apply(lambda x: find_best_match(x, words))
    )

    return df[[column, 'najboljse_ujemanje', 'razmerje', 'za_pregled']]

st.set_page_config(layout="wide")
tabs = [
    stx.TabBarItemData(id="tab1", title="1. Nastavitve", description=""),
    stx.TabBarItemData(id="tab2", title="2. Vnos podatkov", description=""),
    stx.TabBarItemData(id="tab3", title="3. Pregled podatkov", description=""),
    stx.TabBarItemData(id="tab4", title="4. Ročna klasifikacija", description=""),
    stx.TabBarItemData(id="tab5", title="5. Združevanje", description=""),
    stx.TabBarItemData(id="tab6", title="6. Pregled", description=""),
    stx.TabBarItemData(id="tab7", title="7. Prenos", description="")
]

# Create the TabBar with the first tab selected by default
selected_tab = stx.tab_bar(data=tabs, default="tab1")

def load_config(file_path="use_cases.yaml"):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


cols = st.columns([2, 8, 2])  # Create three columns, the middle one takes most space


if selected_tab == "tab1":
    with cols[1]:
        st.header("1. Nastavitve")
        if 'processed_dfs' in st.session_state:
            st.write("Če želite ponovno vnesti podatke osvežite stran.")
        else:
            config = load_config()
            # Display a selectbox for the user to choose a use case
            selected_use_case_name = st.selectbox("Izberi Use Case", list(config["use_cases"].keys()))


            similarity_threshold = st.slider(
                "Izberite prag podobnosti za ujemanje:",
                min_value=0.1,
                max_value=0.9,
                value=st.session_state['similarity_threshold'],
                step=0.1
            )
            st.session_state['similarity_threshold'] = similarity_threshold

            # Fetch the selected use case settings
            st.session_state['usecase'] = config["use_cases"][selected_use_case_name]


# Tab 2: Input Data
elif selected_tab == "tab2":
    with cols[1]:    
        st.header("2. Vnos podatkov")
        if 'usecase' in st.session_state:
            if 'processed_dfs' in st.session_state:
                st.write("Če želite ponovno vnesti podatke osvežite stran.")
            else:
            
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
                            st.session_state['initial_df'] = df
                            unique_words_set = set()  # Use a set to collect unique words

                            preselected = [col.strip() for col in st.session_state['usecase']["columns"].split(',')]

                            # Input for column name
                            selected_columns = st.multiselect(
                                "Izberite stolpce za obdelavo:",
                                options=df.columns.tolist(),
                                default=[col for col in preselected if col in df.columns]
                            )
                            if len(selected_columns) > 0:
                                column_name = ','.join(selected_columns)
                                column_names = [col.strip() for col in column_name.split(',')]
                                for col in column_names:
                                    if col in df.columns:
                                        recognised_column_names.append(col)
                                        unique_words = df[col].dropna().unique()
                                        # Strip words, filter out empty strings, and add unique words to the set
                                        unique_words_set.update([word.strip() for word in unique_words if str(word).strip()])
                                    else:
                                        st.error(f"Stolpec '{col}' ni najden v naloženi CSV datoteki.")

                                # Convert the unique set back to a sorted string for display
                                unique_words_text = ", ".join(sorted(unique_words_set))

                                # Display the unique words
                                st.write("Unikatne besede:")
                                st.text_area(
                                    "Unikatne besede v stolpcih (kopirajte, če je potrebno):",
                                    value=unique_words_text,
                                    height=150,
                                    label_visibility="collapsed"
                                )   
                                if len(recognised_column_names) > 0:
                                    recommended_words = st.session_state['usecase']["recomenders"]
                                    st.write("Priporočen seznam besed:")
                                    st.text_area(
                                        "Priporočene besede:",
                                        value=recommended_words,
                                        height=150,
                                        label_visibility="collapsed"
                                    )
                                else:
                                    st.error(f"Stolpci ne obstajajo v naloženi CSV datoteki.")
                        except pd.errors.EmptyDataError:
                            st.error("CSV datoteka je prazna ali ima napačno obliko.")
                        except csv.Error:
                            st.error("Ni mogoče zaznati ločila v datoteki. Preverite, ali je datoteka pravilno oblikovana." )
                        except Exception as e:
                            st.error(f"Prišlo je do napake pri branju datoteke: {e}")

                if len(recognised_column_names) > 0:
                    st.subheader("Seznam besed za klasifikacijo:")
                    word_input = st.text_area(
                        "Vpiši seznam besed, ločenih z vejicami, za klasifikacijo:",
                        # value=recommended_words,
                        placeholder="npr., telemach, telekom, a1, izi, hot"
                    )
                    
                if word_input:
                    st.session_state['selected_words'] = word_input

                    with st.spinner('Preverjam besede...'):  
                        words = validate_words(word_input)
                    if not words:
                        st.error("Neveljaven vnos. Prosimo, vnesite seznam besed, ločenih z vejicami (npr., telemach, telekom).")
                    else:
                        st.success(f"Veljaven vnos. Za klasifikacijo uporabljenih {len(words)} besed.")

                # Process CSV if everything is valid
                if uploaded_file and word_input and len(recognised_column_names) > 0:
                    try:
                        uploaded_file.seek(0)  # Reset file pointer before processing again
                        
                        with st.spinner('Klasificiram podatke...'):
                            df = pd.read_csv(uploaded_file, delimiter=detected_delimiter)   
                            for column_name in recognised_column_names:  
                                processed_df = process_csv(df, column_name, words)
                                processed_df.sort_values(by="za_pregled", ascending=False, inplace=True)
                                processed_dfs.append(processed_df)
                            
                        if len(processed_dfs) > 0 and 'processed_dfs' not in st.session_state:
                            
                            st.session_state['processed_dfs'] = processed_dfs
    
                            st.session_state['recognised_column_names'] = recognised_column_names
                            st.session_state['words'] = words
                            st.success("CSV datoteka uspešno obdelana!")


                            log_message("tab2 CSV :)")
                        else:
                            st.error("Napaka pri obdelavi CSV datoteke.")
                    except Exception as e:
                        st.error(f"Prišlo je do napake pri obdelavi podatkov: {e}")
        else:
            st.warning("Uredi nastavitve.")                      

elif selected_tab == "tab3":
    with cols[1]:   
        st.header("3. Pregled podatkov")
        if 'usecase' in st.session_state and 'processed_dfs' in st.session_state and 'recognised_column_names' in st.session_state:
            if 'done2_state' not in st.session_state:
                st.session_state['done2_state'] = False  


            done_checkbox = st.checkbox("Done", value=st.session_state['done2_state'])    
            if done_checkbox != st.session_state['done2_state']:
                st.session_state['done2_state'] = done_checkbox  

            if not st.session_state['done2_state']:
                selected_index = st.selectbox(
                    "Izberite stolpec za prikaz podatkov:",
                    range(len(st.session_state['recognised_column_names'])),
                    format_func=lambda x: st.session_state['recognised_column_names'][x],
                    key="selectbox_updated"
                )

                # Display the currently selected DataFrame in an editable data_editor
                st.write(f"Prikazujem podatke za stolpec: {st.session_state['recognised_column_names'][selected_index]}")
                df_to_review = st.session_state['processed_dfs'][selected_index][st.session_state['processed_dfs'][selected_index]['za_pregled'] == True]

                if not df_to_review.empty:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.write("Beseda")
                    with col2:
                        st.write("Najboljše ujemanje")
                    with col3:
                        st.write("Razmerje")
                    with col4:
                        st.write("Označi kot pregledano")
                    for index, row in df_to_review.iterrows():
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.write(row[st.session_state['recognised_column_names'][selected_index]])
                        with col2:
                            st.write(row['najboljse_ujemanje'])
                        with col3:
                            st.write(row['razmerje'])
                        with col4:
                            if st.button(f"Označi kot pregledano", key=f"mark_reviewed_{selected_index}_{index}"):
                                st.session_state['processed_dfs'][selected_index].at[index, 'za_pregled'] = False
                                st.rerun()

        else:
            st.warning("Najprej naloži in preglej podatke.")    




# Tab 4: Manual Classification
elif selected_tab == "tab4":
    with cols[1]:    
        st.header("4. Ročna klasifikacija")

        if 'usecase' in st.session_state and 'processed_dfs' in st.session_state and 'done2_state' in st.session_state and st.session_state['done2_state']==True:

            cols_rocna = st.columns([2, 1])

            with cols_rocna[0]:
                if "staging_changes" not in st.session_state:
                    st.session_state["staging_changes"] = {}

                # Work with a copy of processed_dfs to avoid modifying directly until necessary
                processed_dfs = copy.deepcopy(st.session_state['processed_dfs'])

                for df_index, processed_df in enumerate(processed_dfs):
                    column_name = st.session_state['recognised_column_names'][df_index]

                    # Ensure 'za_pregled' column has no NaN values
                    if 'za_pregled' in processed_df.columns:
                        processed_df['za_pregled'] = processed_df['za_pregled'].fillna(False)

                    # Filter rows for manual classification
                    df_to_check = processed_df[processed_df['za_pregled']].copy()

                    if not df_to_check.empty:
                        st.write(f"Besede za pregled v stolpcu '{column_name}':")

                        # Dropdown options for manual classification
                        dropdown_options = st.session_state['words']

                        # Prepare a staging area for changes specific to the current dataframe
                        if df_index not in st.session_state["staging_changes"]:
                            st.session_state["staging_changes"][df_index] = df_to_check.copy()

                        # Iterate over rows in the dataframe requiring review
                        for index, row in df_to_check.iterrows():
                            original_value = row[column_name]  # Original value for classification
                            staged_row = st.session_state["staging_changes"][df_index].loc[index]

                            # Selectbox for user input
                            new_match = st.selectbox(
                                f"Uredi najboljše ujemanje za vrstico {index + 1} (Prvotna vrednost: {original_value}):",
                                options=dropdown_options,
                                index=dropdown_options.index(staged_row['najboljse_ujemanje'])
                                if staged_row['najboljse_ujemanje'] in dropdown_options
                                else dropdown_options.index("neznano"),
                                key=f"selectbox_{df_index}_{index}"
                            )

                            # Update the staging area with the new value
                            st.session_state["staging_changes"][df_index].at[index, 'najboljse_ujemanje'] = new_match

            with cols_rocna[1]:
                if st.button("Shrani vse spremembe"):
                    for df_index, staged_df in st.session_state["staging_changes"].items():
                        # Update the original DataFrame with changes from the staging area
                        for index in staged_df.index:
                            original_value = st.session_state['processed_dfs'][df_index].loc[index, 'najboljse_ujemanje']
                            new_value = staged_df.loc[index, 'najboljse_ujemanje']

                            # Only mark 'za_pregled' as False if the value has changed
                            if original_value != new_value:
                                st.session_state['processed_dfs'][df_index].at[index, 'najboljse_ujemanje'] = new_value
                                st.session_state['processed_dfs'][df_index].at[index, 'za_pregled'] = False

                    # Clear the staging area after saving changes
                    st.session_state["staging_changes"] = {}
                    st.success("Vse spremembe so shranjene.")

        else:
            st.warning("Najprej naloži in preglej podatke.")

# Tab 5: Združi rezultate
elif selected_tab == "tab5":
    with cols[1]:    
        st.header("5. Združevanje in preimenovanje")
            
        if 'usecase' in st.session_state and 'processed_dfs' in st.session_state and 'done2_state' in st.session_state and st.session_state['done2_state']==True:
            
            if  'selected_words' in st.session_state:
                selected_words = validate_words(st.session_state['selected_words'])
                if selected_words:
                    not_in_any = [word for word in selected_words if word not in st.session_state['usecase']["mergers"] and word not in st.session_state['usecase']["renamers"] and word not in st.session_state['usecase']["identificators"]]
                    if not_in_any:
                        st.write("Besede, ki niso v pravilih združevanja, preimenovanja ali identifikatorjih:")
                        for word in not_in_any:
                            col1, col2, col3, col4, col5, col6 = st.columns(6)
                            with col2:
                                st.write(word)
                            with col3:
                                if st.button(f"Dodaj v združevanje", key=f"add_merger_{word}"):
                                    st.session_state['usecase']["mergers"][word] = word
                                    st.rerun()
                            with col4:
                                if st.button(f"Dodaj v preimenovanje", key=f"add_renamer_{word}"):
                                    st.session_state['usecase']["renamers"][word] = word
                                    st.rerun()
                            with col5:
                                if st.button(f"Dodaj v identifikatorje", key=f"add_identifier_{word}"):

                                    valid_identifiers = {k: v for k, v in st.session_state['usecase']["identificators"].items() if k not in ["drugo", "ne vem", "neznano"]}
                                    st.session_state['usecase']["identificators"][word] = str(max(int(value) for value in valid_identifiers.values()) + 1)
                                    st.rerun()

            st.subheader("Pravila za združevanje rezultatov:")
            if 'merge_edited_switcher' in st.session_state and 'processed_dfs':
                merge_switcher = st.session_state['merge_edited_switcher']
            else:
                merge_switcher = st.session_state['usecase']["mergers"]   
            merger_df = pd.DataFrame(list(merge_switcher.items()), columns=["Iz besede", "V besedo"])
            
            left_col, right_col = st.columns([5, 1])  
            with left_col:            
                edited_merger_switcher_df = st.data_editor(
                    merger_df,
                    num_rows="dynamic",  # Uporabniki lahko dodajo nove vrstice
                    use_container_width=True
                )
            with right_col:
                if st.button("Shrani spremembe", key="save_mergers"):          
                    merge_edited_switcher = dict(zip(edited_merger_switcher_df["Iz besede"], edited_merger_switcher_df["V besedo"]))
                    st.session_state['merge_edited_switcher'] = merge_edited_switcher



            st.subheader("Pravila za preimenovanje rezultatov:")
            if 'rename_edited_switcher' in st.session_state and 'processed_dfs':
                rename_switcher = st.session_state['rename_edited_switcher']
            else:
                rename_switcher = st.session_state['usecase']["renamers"]             
            renamer_df = pd.DataFrame(list(rename_switcher.items()), columns=["Izvirno ime", "Novo ime"])
            log_message("tab5 edited rename_edited_switcher")

            left_col, right_col = st.columns([5, 1])  
            with left_col:       
                edited_renamer_renamer_df = st.data_editor(
                    renamer_df,
                    num_rows="dynamic",  # Uporabniki lahko dodajo nove vrstice
                    use_container_width=True
                )
            
            with right_col:
                if st.button("Shrani spremembe", key="save_renamers"):   
                    rename_edited_switcher = dict(zip(edited_renamer_renamer_df["Izvirno ime"], edited_renamer_renamer_df["Novo ime"]))
                    st.session_state['rename_edited_switcher'] = rename_edited_switcher


            st.subheader("Identifikatorji:")
            if 'edited_identifiers' in st.session_state :
                default_identifiers = st.session_state['edited_identifiers']
            else:
                default_identifiers = st.session_state['usecase']["identificators"]   

            identifier_df = pd.DataFrame(list(default_identifiers.items()), columns=["Ime", "Identifikator"])
            
            left_col, right_col = st.columns([5, 1])  
            with left_col: 
                edited_identifier_df = st.data_editor(
                    identifier_df,
                    num_rows="dynamic",  
                    use_container_width=True,
                )
                
            with right_col:
                if st.button("Shrani spremembe", key="save_identifiers"):   
                    edited_identifiers = dict(zip(edited_identifier_df["Ime"], edited_identifier_df["Identifikator"]))  
                    st.session_state['edited_identifiers'] = edited_identifiers   
            
            
        else:
            st.warning("Najprej naloži in preglej podatke.")    

# Tab 6: Dodaj identifikatorje
elif selected_tab == "tab6":
    with cols[1]:    
        st.header("6. Pregled rezultatov")
        
        if 'usecase' in st.session_state and 'processed_dfs' in st.session_state and 'recognised_column_names' in st.session_state  and 'done2_state' in st.session_state and st.session_state['done2_state']==True:

            if 'merge_edited_switcher' in st.session_state and 'processed_dfs':
                merge_edited_switcher = st.session_state['merge_edited_switcher']
            else:
                merge_edited_switcher = st.session_state['usecase']["mergers"]   

            if 'rename_edited_switcher' in st.session_state and 'processed_dfs':
                rename_edited_switcher = st.session_state['rename_edited_switcher']
            else:
                rename_edited_switcher = st.session_state['usecase']["renamers"]      

            if 'edited_identifiers' in st.session_state :
                edited_identifiers = st.session_state['edited_identifiers']
            else:
                edited_identifiers = st.session_state['usecase']["identificators"]  


   
            def zdruzi_best_match(name):
                if name is None or pd.isna(name):
                    return name  # Če je vrednost None ali NaN, jo pustimo nespremenjeno
                return merge_edited_switcher.get(name.lower(), name)  
            
            def rename_best_match(name):
                if name is None or pd.isna(name):
                    return name  # Če je vrednost None ali NaN, jo pustimo nespremenjeno
                return rename_edited_switcher.get(name.lower(), name)     
            
        # Funkcija za pridobitev identifikatorja
            def get_identifier(name):
                max_identifier = max(int(value) for value in edited_identifiers.values())
                if name is None or pd.isna(name):
                    return None  
                return edited_identifiers.get(name.lower(), max_identifier)        
    

            processed_dfs = st.session_state['processed_dfs']
            updated_dfs = copy.deepcopy(processed_dfs)

            for df_index, processed_df in enumerate(processed_dfs):
                
                processed_df['najboljse_ujemanje'] = processed_df['najboljse_ujemanje'].apply(zdruzi_best_match)
                updated_dfs[df_index]['najboljse_ujemanje'] = processed_df['najboljse_ujemanje'].apply(rename_best_match)
                updated_dfs[df_index]['identifikator'] = processed_df['najboljse_ujemanje'].apply(get_identifier)
                updated_dfs[df_index].drop(['za_pregled'], axis=1, inplace=True)
                updated_dfs[df_index].drop(['razmerje'], axis=1, inplace=True)


            # Dropdown to select which updated_df DataFrame to display
            selected_column = st.selectbox(
                "Izberite stolpec za prikaz obdelanih podatkov:",
                st.session_state['recognised_column_names'],
                key="selectbox_tab4"
            )

            # Get the index of the selected column
            selected_index = st.session_state['recognised_column_names'].index(selected_column)
            df_to_display = updated_dfs[selected_index]

            st.write(f"Posodobljeni podatki za stolpec '{selected_column}':")
            st.dataframe(df_to_display)
            st.session_state['updated_dfs'] = updated_dfs    
            st.session_state['viewed_results'] = True
            log_message("tab6 viewed_results")
        else:
            st.warning("Pripravi podatke in pravila za združevanje v prejšnjih zavihkih.")


elif selected_tab == "tab7":
    with cols[1]:    
        st.header("7. Prenos rezultatov")

        if 'usecase' in st.session_state and 'updated_dfs' in st.session_state and 'initial_df' in st.session_state and 'recognised_column_names' in st.session_state and 'viewed_results' in st.session_state and st.session_state['viewed_results']==True:
            log_message("tab7 INNNNNN")
            initial_df = st.session_state['initial_df']
            final_df = initial_df.copy()
            updated_dfs = st.session_state['updated_dfs']
            for df_index, updated_df in enumerate(updated_dfs):
                column_name = st.session_state['recognised_column_names'][df_index]
                log_message("tab7 " + column_name + "_najboljse_ujemanje")
                col_index = final_df.columns.get_loc(column_name) + 1

                if column_name + "_najboljse_ujemanje" not in final_df.columns:
                    final_df.insert(col_index, column_name + "_najboljse_ujemanje", updated_df['najboljse_ujemanje'])
                else:
                    st.warning(f"Stolpec '{column_name + '_najboljse_ujemanje'}' že obstaja v končni datoteki.")
                if column_name + "R" not in final_df.columns:
                    final_df.insert(col_index + 1, column_name + "R", updated_df['identifikator'])
                else:
                    st.warning(f"Stolpec '{column_name + 'R'}' že obstaja v končni datoteki.")


            st.write(f"CSV za izvox':")
            st.dataframe(final_df)  


            csv = final_df.to_csv(index=False, sep=';').encode('utf-8')
            st.download_button(
                label="Prenesi končni CSV",
                data=csv,
                file_name="končni_podatki.csv",
                mime="text/csv",
            )
        else:
            st.warning("Ni končnih podatkov za prikaz!")                