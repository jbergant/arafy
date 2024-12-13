import streamlit as st
import pandas as pd
import Levenshtein
import csv
import copy

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

        if highest_similarity > 0.7:
            return best_match, highest_similarity, False
        else:
            return best_match, highest_similarity, True

    # Uporabi funkcijo na določen stolpec
    df['najboljse_ujemanje'], df['razmerje'], df['za_pregled'] = zip(
        *df[column].astype(str).apply(lambda x: find_best_match(x, words))
    )

    return df[[column, 'najboljse_ujemanje', 'razmerje', 'za_pregled']]

# Streamlit Tabs
tab1, tab2, tab3, tab4, tab5, tab6  = st.tabs(["1. Vnos podatkov", "2. Pregled podatkov", "3. Ročna klasifikacija", "4. Združevanje in preimenovanje", "5. Pregled rezultatov", "6. Prenos rezultatov"])

# Tab 1: Input Data
with tab1:
    st.header("1. Vnos podatkov")
    if 'processed_dfs' in st.session_state:
        st.write("Če želite ponovno vnesti podatke osvežite stran.")
    else:
        st.write("Naloži CSV datoteko in vnesi ime stolpca.")
        # File uploader
        uploaded_file = st.file_uploader("Naloži CSV", type="csv")

        # Input for column name
        column_name = st.text_input(
            "Vnesite ime stolpca ločeno z vejico:",
            # value="Q1a_1_other,Q1a_2_other,Q1a_3_other",
            placeholder="npr., Q1a_1_other, Q1a_2_other, Q1a_3_other"
        )
        recognised_column_names = []
        processed_dfs = []
        word_input = None

        if uploaded_file and column_name:
            column_names = [col.strip() for col in column_name.split(',')]
            try:
                uploaded_file.seek(0)  
                sample = uploaded_file.read(1024).decode('utf-8')  
                uploaded_file.seek(0)  
                detected_delimiter = csv.Sniffer().sniff(sample).delimiter 

                df = pd.read_csv(uploaded_file, delimiter=detected_delimiter)
                st.session_state['initial_df'] = df

                for col in column_names:
                    if col in df.columns:
                        recognised_column_names.append(col)
                        unique_words = df[col].dropna().unique()
                        unique_words = [str(word).strip() for word in unique_words]
                        unique_words_text = ", ".join(unique_words)

                        st.write(f"Unikatne besede v stolpcu '{col}':")
                        st.text_area(
                            f"Unikatne besede v stolpcu '{col}' (kopirajte, če je potrebno):",
                            value=unique_words_text,
                            height=150,
                            label_visibility="collapsed"
                        )
                    else:
                        st.error(f"Stolpec '{col}' ni najden v naloženi CSV datoteki.")

        
                if len(recognised_column_names) > 0:
                    recommended_words = "telemach, telekom, a1, a1 slovenija, izimobil, t2, hofer, simobil, hot, bob, hot telekom, hofer telekom, t-2, mobitel, izi, spar mobil, telekom slovenije, izi mobil, tuš mobil, tuš, re do, hot mobil, siol, re:do"
                    st.write("Priporočen seznam besed:")
                    st.text_area(
                        "Priporočene besede:",
                        value=recommended_words,
                        height=150,
                        label_visibility="collapsed"
                    )
                else:
                    st.error(f"Stolpeci ne obstajajo v naloženi CSV datoteki.")
            except pd.errors.EmptyDataError:
                st.error("CSV datoteka je prazna ali ima napačno obliko.")
            except csv.Error:
                st.error("Ni mogoče zaznati ločila v datoteki. Preverite, ali je datoteka pravilno oblikovana.")
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
                """Obdelaj CSV datoteko in izračunaj najboljše Levenshteinovo ujemanje za vsako besedo."""
                
                with st.spinner('Klasificiram podatke...'):
                    df = pd.read_csv(uploaded_file, delimiter=detected_delimiter)   
                    for column_name in recognised_column_names:  
                        processed_df = process_csv(df, column_name, words)
                        processed_dfs.append(processed_df)
                    
                if len(processed_dfs) > 0:
                    st.session_state['processed_dfs'] = processed_dfs
                    st.session_state['recognised_column_names'] = recognised_column_names
                    st.session_state['words'] = words
                    st.success("CSV datoteka uspešno obdelana!")


        
                else:
                    st.error("Napaka pri obdelavi CSV datoteke.")
            except Exception as e:
                st.error(f"Prišlo je do napake pri obdelavi podatkov: {e}")

with tab2:
    st.header("2. Pregled podatkov")
    if 'processed_dfs' in st.session_state and 'recognised_column_names' in st.session_state:
        if 'done2_state' not in st.session_state:
            st.session_state['done2_state'] = False  
        if 'selected_column' not in st.session_state:
            st.session_state['selected_column'] = st.session_state['recognised_column_names'][0]  

        done_checkbox = st.checkbox("Done", value=st.session_state['done2_state'])    
        if done_checkbox != st.session_state['done2_state']:
            st.session_state['done2_state'] = done_checkbox     
           


            changes = st.session_state['selectbox_updated_' + str(st.session_state['selected_column'])]
            changed_index = st.session_state['recognised_column_names'].index(st.session_state['selected_column'])
            for row_idx, row_changes in changes.get("edited_rows", {}).items():
                for col, new_value in row_changes.items():
                    st.session_state['processed_dfs'][changed_index].at[int(row_idx), col] = new_value     




        if st.session_state['done2_state'] is False:
            updated_selected_column = st.selectbox(
                "Izberite stolpec za prikaz podatkov:",
                st.session_state['recognised_column_names'],
                key="selectbox_updated",
            )

            if(st.session_state['selected_column'] != updated_selected_column):
                st.write("index changed from " + str(st.session_state['selected_column']) + " to " + str(updated_selected_column))
                changes = st.session_state['selectbox_updated_' + str(st.session_state['selected_column'])]
                changed_index = st.session_state['recognised_column_names'].index(st.session_state['selected_column'])
                for row_idx, row_changes in changes.get("edited_rows", {}).items():
                    for col, new_value in row_changes.items():
                        st.session_state['processed_dfs'][changed_index].at[int(row_idx), col] = new_value                
            
            
            st.session_state['selected_column'] = updated_selected_column
            
            # Get the index of the selected column
            selected_index = st.session_state['recognised_column_names'].index(updated_selected_column)


                

            editable_df_placeholder = st.empty()
            with editable_df_placeholder.container():
        
                df_to_edit = copy.deepcopy(st.session_state['processed_dfs'][selected_index])
                df_to_edit = df_to_edit.sort_values(by="za_pregled", ascending=False)
                st.write(f"Obdelani podatki za stolpec '{updated_selected_column}':")
                # Make 'za_pregled' column editable
                editable_df = st.data_editor(
                    df_to_edit,
                    column_config={
                        "za_pregled": st.column_config.CheckboxColumn("Za pregled")
                    },
                    num_rows="fixed",
                    key="selectbox_updated_" + str(updated_selected_column),
                    use_container_width=True
                )
    else:
        st.warning("Najprej naloži in obdelaj podatke v zavihku '1. Vnos podatkov'.")


# Tab 3: Manual Classification
with tab3:
    st.header("3. Ročna klasifikacija")
    
    if 'processed_dfs' in st.session_state and 'recognised_column_names' in st.session_state and 'done2_state' in st.session_state and st.session_state['done2_state']:

        # Ensure 'za_pregled' column has no NaN values
        processed_dfs = copy.deepcopy(st.session_state['processed_dfs'])

        for df_index, processed_df in enumerate(processed_dfs):
            column_name = st.session_state['recognised_column_names'][df_index]
            if 'za_pregled' in processed_df.columns:
                processed_df['za_pregled'] = processed_df['za_pregled'].fillna(False)

            # Filter rows for manual classification
            df_to_check = processed_df[processed_df['za_pregled']]

            if not df_to_check.empty:
                st.write("Vrstice za pregled:")

                # Priprava možnosti za spustni seznam
                dropdown_options = ["neznano"] + st.session_state['words']
                
                # Dodajanje spustnega seznama za "najboljše ujemanje"
                for index, row in df_to_check.iterrows():
                    original_value = row[column_name]  # Prvotna vrednost za klasifikacijo
                    new_match = st.selectbox(
                        f"Uredi najboljše ujemanje za vrstico {index + 1} (Prvotna vrednost: {original_value}):",
                        options=dropdown_options,
                        index=dropdown_options.index(row['najboljse_ujemanje']) 
                        if row['najboljse_ujemanje'] in dropdown_options 
                        else dropdown_options.index("neznano"),
                        key=f"selectbox_{df_index}_{index}"  # Unique key using df_index and row index
                    )
                    df_to_check.at[index, 'najboljse_ujemanje'] = new_match
                    if new_match != row['najboljse_ujemanje']:
                        df_to_check.at[index, 'za_pregled'] = False
                
                # Shrani urejen DataFrame
                st.session_state['processed_dfs'][df_index] = df_to_check
            else:
                st.success("Ni vrstic za pregled!")
    else:
        st.warning("Najprej naloži in preglej podatke.")

# Tab 4: Združi rezultate
with tab4:
    st.header("3. Združevanje in preimenovanje")
    
    # if 'processed_dfs' in st.session_state and 'recognised_column_names' in st.session_state:
    #     st.subheader("Pravila za združevanje rezultatov:")

    #     merge_switcher = {
    #         "telekom slovenije": "telekom",
    #         "a1 slovenija": "a1",
    #         "hofer": "hot",
    #         "hot mobil": "hot",
    #         "hot telekom": "hot",
    #         "hofer telekom": "hot",
    #         "izi mobil": "a1",
    #         "t-2": "t2",
    #         "mobitel": "telekom",
    #         "simobil": "a1",
    #         "tuš mobil": "telemach",
    #         "tuš": "telemach",
    #         "siol": "telekom",
    #     }
        
    #     # Pretvorimo slovar v DataFrame za urejanje
    #     merger_df = pd.DataFrame(list(merge_switcher.items()), columns=["Izvirno ime", "Novo ime"])
        
    #     # Uporabnikom omogočimo urejanje DataFrame-a
    #     edited_merger_switcher_df = st.data_editor(
    #         merger_df,
    #         num_rows="dynamic",  # Uporabniki lahko dodajo nove vrstice
    #         use_container_width=True
    #     )
        
    #     # Pretvorimo urejeni DataFrame nazaj v slovar
    #     merge_edited_switcher = dict(zip(edited_merger_switcher_df["Izvirno ime"], edited_merger_switcher_df["Novo ime"]))
    #     st.session_state['merge_edited_switcher'] = merge_edited_switcher


    #     st.subheader("Identifikatorji:")

    #     # Privzeti slovar za identifikatorje
    #     default_identifiers = {
    #         "telekom": "1",
    #         "a1": "2",
    #         "telemach": "3",
    #         "t2": "4",
    #         "bob": "5",
    #         "hot": "6",
    #         "re:do": "7",
    #     }
        
    #     # Pretvorimo slovar v DataFrame za urejanje
    #     identifier_df = pd.DataFrame(list(default_identifiers.items()), columns=["Ime", "Identifikator"])
        
    #     # Uporabnikom omogočimo urejanje DataFrame-a
    #     edited_identifier_df = st.data_editor(
    #         identifier_df,
    #         num_rows="dynamic",  # Uporabniki lahko dodajo nove vrstice
    #         use_container_width=True
    #     )
        
    #     # Pretvorimo urejeni DataFrame nazaj v slovar
    #     edited_identifiers = dict(zip(edited_identifier_df["Ime"], edited_identifier_df["Identifikator"]))  
    #     st.session_state['edited_identifiers'] = edited_identifiers      
    # else:
    #     st.warning("Najprej naloži in obdelaj podatke v zavihku '1. Vnos podatkov'.")

# Tab 5: Dodaj identifikatorje
with tab5:
    st.header("4. Pregled rezultatov")
    
    # if 'processed_dfs' in st.session_state and 'recognised_column_names' in st.session_state and 'merge_edited_switcher' in st.session_state and 'edited_identifiers' in st.session_state:
    #     # Privzeti slovar za identifikatorje

    #     merge_edited_switcher = st.session_state['merge_edited_switcher']
    #     edited_identifiers = st.session_state['edited_identifiers']
    #     # Funkcija za preimenovanje z uporabniškim slovarjem
    #     def rename_best_match(name):
    #         if name is None or pd.isna(name):
    #             return name  # Če je vrednost None ali NaN, jo pustimo nespremenjeno
    #         return merge_edited_switcher.get(name.lower(), name)     
        
    #    # Funkcija za pridobitev identifikatorja
    #     def get_identifier(name):
    #         if name is None or pd.isna(name):
    #             return "8"  # Če je vrednost None ali NaN, privzeti identifikator
    #         return edited_identifiers.get(name.lower(), "8")        
 

    #     processed_dfs = st.session_state['processed_dfs']
    #     updated_dfs = copy.deepcopy(processed_dfs)
    #     for df_index, processed_df in enumerate(processed_dfs):
    #         updated_dfs[df_index]['najboljse_ujemanje'] = processed_df['najboljse_ujemanje'].apply(rename_best_match)

    #     for df_index, updated_df in enumerate(updated_dfs):
    #         updated_dfs[df_index]['identifikator'] = updated_df['najboljse_ujemanje'].apply(get_identifier)



    #     # Dropdown to select which updated_df DataFrame to display
    #     selected_column = st.selectbox(
    #         "Izberite stolpec za prikaz obdelanih podatkov:",
    #         st.session_state['recognised_column_names'],
    #         key="selectbox_tab4"
    #     )

    #     # Get the index of the selected column
    #     selected_index = st.session_state['recognised_column_names'].index(selected_column)
    #     df_to_display = updated_dfs[selected_index]

    #     st.write(f"Posodobljeni podatki za stolpec '{selected_column}':")
    #     st.dataframe(df_to_display)
    #     st.session_state['updated_dfs'] = updated_dfs      
    # else:
    #     st.warning("Pripravi podatke in pravila za združevanje v prejšnjih zavihkih.")


with tab6:
    st.header("5. Prenos rezultatov")

    # if 'updated_dfs' in st.session_state and 'initial_df' in st.session_state and 'recognised_column_names' in st.session_state:
    #     st.write("Končni podatki po klasifikaciji:")
    #     initial_df = st.session_state['initial_df']
    #     final_df = initial_df.copy()
    #     updated_dfs = st.session_state['updated_dfs']
    #     for df_index, updated_df in enumerate(updated_dfs):
    #         column_name = st.session_state['recognised_column_names'][df_index]
            
    #         # Insert the new columns right after the original column
    #         col_index = final_df.columns.get_loc(column_name) + 1
    #         final_df.insert(col_index, column_name + "_najboljse_ujemanje", updated_df['najboljse_ujemanje'])
    #         final_df.insert(col_index + 1, column_name + "_identifikator", updated_df['identifikator'])


    #     st.write(f"CSV za izvox':")
    #     st.dataframe(final_df)  


    #     # Prenesi končno datoteko
    #     csv = final_df.to_csv(index=False).encode('utf-8')
    #     st.download_button(
    #         label="Prenesi končni CSV",
    #         data=csv,
    #         file_name="končni_podatki.csv",
    #         mime="text/csv",
    #     )
    # else:
    #     st.warning("Ni končnih podatkov za prikaz!")