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
tab1, tab2, tab3, tab4, tab5, tab6, tab7  = st.tabs([ "1. Nastavitve", "2. Vnos podatkov", "3. Pregled podatkov", "4. Ročna klasifikacija", "5. Združevanje", "6. Pregled", "7. Prenos"])




with tab1:
    use_cases = {
        "Mobilni ponudniki": {
            "mergers": {
                "a1 slovenija": "a1",
                "hofer": "hot",
                "hot mobil": "hot",
                "hot telekom": "hot",
                "hofer telekom": "hot",
                "telekom slovenije": "telekom",
                "t-2": "t2",
            },
            "renamers": {
                "mobitel": "telekom",
                "simobil": "a1",
                "tuš mobil": "telemach",
                "tuš": "telemach",
                "izi mobil": "a1",
                "siol": "telekom",
            },
            "identificators": {
                "telekom": "1",
                "a1": "2",
                "telemach": "3",
                "t2": "4",
                "bob": "5",
                "hot": "6",
                "re:do": "7",
            },
            "columns": "Q1a_1_other,Q1a_2_other,Q1a_3_other",
            "recomenders":  "telemach, telekom, a1, a1 slovenija, izimobil, t2, hofer, simobil, hot, bob, hot telekom, hofer telekom, t-2, mobitel, izi, spar mobil, telekom slovenije, izi mobil, tuš mobil, tuš, re do, hot mobil, siol, re:do"
        },
        "Fiksni ponudniki": {
            "mergers": {
                "a1 slovenija": "a1",
                "a2": "a1",
                "hofer": "hot",
                "hot mobil": "hot",
                "hot telekom": "hot",
                "hofer telekom": "hot",
                "telekom slovenije": "telekom",
                "t-2": "t2",
            },
            "renamers": {
                "mobitel": "telekom",
                "simobil": "a1",
                "tuš mobil": "telemach",
                "tuš": "telemach",
                "izi mobil": "a1",
                "siol": "telekom",
                "amis": "a1",
                "ario": "telemach",
                "neo": "telekom",
            },
            "identificators": {
                "telekom": "1",
                "a1": "2",
                "telemach": "3",
                "t2": "4",
                "Total TV": "5",
            },
            "columns": "Q1b_1_other,Q1b_2_other,Q1b_3_other",
            "recomenders":  "a1, a1 slovenija, amis, ario, bob, hot, hofer, hofer telekom, hofer hot, mobitel, neo, siol, samsung, sanmix, simobil, svislar, t2, t1, telekom, telekom slovenije, telemach, tvspored, totaltv"
        },        
        "Other Use Case 1": {
            "mergers": {"example1": "merged_example1"},
            "renamers": {"example2": "renamed_example2"},
            "identificators": {"example3": "1"},
            "columns": "example1, example2, example3",
            "recomenders": "example1, example2, example3",
        },
        "Other Use Case 2": {
            "mergers": {"example4": "merged_example4"},
            "renamers": {"example5": "renamed_example5"},
            "identificators": {"example6": "1"},
            "columns": "example1, example2, example3",
            "recomenders": "example1, example2, example3",
        },
    }

    # Display a selectbox for the user to choose a use case
    selected_use_case_name = st.selectbox("Izberite primer uporabe:", list(use_cases.keys()))

    # Fetch the selected use case settings
    st.session_state['usecase'] = use_cases[selected_use_case_name]



# Tab 2: Input Data
with tab2:
    st.header("1. Vnos podatkov")
    if 'usecase' in st.session_state:
        if 'processed_dfs' in st.session_state:
            st.write("Če želite ponovno vnesti podatke osvežite stran.")
        else:
           
            st.write("Naloži CSV datoteko in vnesi ime stolpca.")
            # File uploader
            uploaded_file = st.file_uploader("Naloži CSV", type="csv")

            # Input for column name
            column_name = st.text_input(
                "Vnesite ime stolpca ločeno z vejico:",
                # value=st.session_state['usecase']["columns"],
                placeholder="npr." + st.session_state['usecase']["columns"]
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
                    unique_words_set = set()  # Use a set to collect unique words

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
                            processed_df.sort_values(by="za_pregled", ascending=False, inplace=True)
                            processed_dfs.append(processed_df)
                        
                    if len(processed_dfs) > 0 and 'processed_dfs' not in st.session_state:
                        
                        st.session_state['processed_dfs'] = processed_dfs
                        # st.write("DataFrame ID cccc:", id(st.session_state['processed_dfs'][0]))
                        # st.write("DataFrame ID cccc:", id(st.session_state['processed_dfs'][1]))
                        # st.write("DataFrame ID cccc:", id(st.session_state['processed_dfs'][2]))
                        st.session_state['recognised_column_names'] = recognised_column_names
                        st.session_state['words'] = words
                        st.success("CSV datoteka uspešno obdelana!")


            
                    else:
                        st.error("Napaka pri obdelavi CSV datoteke.")
                except Exception as e:
                    st.error(f"Prišlo je do napake pri obdelavi podatkov: {e}")
    else:
        st.warning("Uredi nastavitve.")                      
with tab3:
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
            # Create two columns: one for the data editor (left) and one for other elements (right)
            left_col, right_col = st.columns([5, 1])  # Adjust proportions as needed (e.g., 3:1 for 75% and 25% width split)

            # Place the data editor in the left column
            with left_col:
                edited_df = st.data_editor(
                    st.session_state['processed_dfs'][selected_index],
                    num_rows="dynamic",  # Allow dynamic rows
                    key=f"editable_df_{selected_index}"  # Unique key for each DataFrame
                )

            # Place other elements, like the button, in the right column
            with right_col:
                if st.button("Shrani spremembe"):
                    # Update the session state with the edited DataFrame
                    st.session_state['processed_dfs'][selected_index] = edited_df
                    st.toast(f"Spremembe za stolpec '{st.session_state['recognised_column_names'][selected_index]}' so shranjene!")

            # Display the updated DataFrame from session state
            # st.write("Posodobljena tabela:", st.session_state['processed_dfs'][selected_index])
    else:
        st.warning("Najprej naloži in preglej podatke.")    




# Tab 4: Manual Classification
with tab4:
    st.header("3. Ročna klasifikacija")

    if 'usecase' in st.session_state and 'processed_dfs' in st.session_state and 'recognised_column_names' in st.session_state and 'done2_state' in st.session_state and st.session_state['done2_state']:

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
                st.write("Vrstice za pregled:")

                # Dropdown options for manual classification
                dropdown_options = ["neznano"] + st.session_state['words']

                # Add dropdown menus for each row requiring review
                for index, row in df_to_check.iterrows():
                    original_value = row[column_name]  # Original value for classification
                    new_match = st.selectbox(
                        f"Uredi najboljše ujemanje za vrstico {index + 1} (Prvotna vrednost: {original_value}):",
                        options=dropdown_options,
                        index=dropdown_options.index(row['najboljse_ujemanje'])
                        if row['najboljse_ujemanje'] in dropdown_options
                        else dropdown_options.index("neznano"),
                        key=f"selectbox_{df_index}_{index}"  # Unique key for each dropdown
                    )

                    # Update the row with the new classification
                    df_to_check.at[index, 'najboljse_ujemanje'] = new_match

                    # If the match is changed, mark 'za_pregled' as False
                    if new_match != row['najboljse_ujemanje']:
                        df_to_check.at[index, 'za_pregled'] = False

                # Update only the rows in df_to_check back into the original DataFrame
                processed_df.update(df_to_check)
                st.session_state['processed_dfs'][df_index] = processed_df  # Save the updated DataFrame
            else:
                st.success("Ni vrstic za pregled!")
    else:
        st.warning("Najprej naloži in preglej podatke.")

# Tab 5: Združi rezultate
with tab5:
    st.header("4. Združevanje in preimenovanje")
    
    if 'usecase' in st.session_state and 'processed_dfs' in st.session_state and 'recognised_column_names' in st.session_state and 'done2_state' in st.session_state and st.session_state['done2_state']:
        st.subheader("Pravila za združevanje rezultatov:")

        merge_switcher = st.session_state['usecase']["mergers"]

        # Pretvorimo slovar v DataFrame za urejanje
        merger_df = pd.DataFrame(list(merge_switcher.items()), columns=["Iz besede", "V besedo"])
        
        # Uporabnikom omogočimo urejanje DataFrame-a
        edited_merger_switcher_df = st.data_editor(
            merger_df,
            num_rows="dynamic",  # Uporabniki lahko dodajo nove vrstice
            use_container_width=True
        )
        
        # Pretvorimo urejeni DataFrame nazaj v slovar
        merge_edited_switcher = dict(zip(edited_merger_switcher_df["Iz besede"], edited_merger_switcher_df["V besedo"]))
        st.session_state['merge_edited_switcher'] = merge_edited_switcher




        st.subheader("Pravila za preimenovanje rezultatov:")
        rename_switcher = st.session_state['usecase']["renamers"]
         
        # Pretvorimo slovar v DataFrame za urejanje
        renamer_df = pd.DataFrame(list(rename_switcher.items()), columns=["Izvirno ime", "Novo ime"])
        
        # Uporabnikom omogočimo urejanje DataFrame-a
        edited_renamer_renamer_df = st.data_editor(
            renamer_df,
            num_rows="dynamic",  # Uporabniki lahko dodajo nove vrstice
            use_container_width=True
        )
        
        # Pretvorimo urejeni DataFrame nazaj v slovar
        rename_edited_switcher = dict(zip(edited_renamer_renamer_df["Izvirno ime"], edited_renamer_renamer_df["Novo ime"]))
        st.session_state['rename_edited_switcher'] = rename_edited_switcher





        st.subheader("Identifikatorji:")

        default_identifiers = st.session_state['usecase']["identificators"]    
        # Pretvorimo slovar v DataFrame za urejanje
        identifier_df = pd.DataFrame(list(default_identifiers.items()), columns=["Ime", "Identifikator"])
        
        # Uporabnikom omogočimo urejanje DataFrame-a
        edited_identifier_df = st.data_editor(
            identifier_df,
            num_rows="dynamic",  # Uporabniki lahko dodajo nove vrstice
            use_container_width=True
        )
        
        # Pretvorimo urejeni DataFrame nazaj v slovar
        edited_identifiers = dict(zip(edited_identifier_df["Ime"], edited_identifier_df["Identifikator"]))  
        st.session_state['edited_identifiers'] = edited_identifiers      
    else:
        st.warning("Najprej naloži in preglej podatke.")    

# Tab 6: Dodaj identifikatorje
with tab6:
    st.header("4. Pregled rezultatov")
    
    if 'usecase' in st.session_state and 'processed_dfs' in st.session_state and 'recognised_column_names' in st.session_state  and 'done2_state' in st.session_state and st.session_state['done2_state'] and 'merge_edited_switcher' in st.session_state and 'edited_identifiers' in st.session_state:
        # Privzeti slovar za identifikatorje


        merge_edited_switcher = st.session_state['merge_edited_switcher']
        rename_edited_switcher = st.session_state['rename_edited_switcher']
        edited_identifiers = st.session_state['edited_identifiers']
        # Funkcija za preimenovanje z uporabniškim slovarjem
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
            max_identifier = max(int(value) for value in edited_identifiers.values()) + 1
            if name is None or pd.isna(name):
                return max_identifier  # Če je vrednost None ali NaN, MAX identifikator
            return edited_identifiers.get(name.lower(), max_identifier)        
 

        processed_dfs = st.session_state['processed_dfs']
        updated_dfs = copy.deepcopy(processed_dfs)

        for df_index, processed_df in enumerate(processed_dfs):
            updated_dfs[df_index]['najboljse_ujemanje'] = processed_df['najboljse_ujemanje'].apply(zdruzi_best_match)
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
    else:
        st.warning("Pripravi podatke in pravila za združevanje v prejšnjih zavihkih.")


with tab7:
    st.header("7. Prenos rezultatov")

    if 'usecase' in st.session_state and 'updated_dfs' in st.session_state and 'initial_df' in st.session_state and 'recognised_column_names' in st.session_state and 'done2_state' in st.session_state and st.session_state['done2_state']:
        st.write("Končni podatki po klasifikaciji:")
        initial_df = st.session_state['initial_df']
        final_df = initial_df.copy()
        updated_dfs = st.session_state['updated_dfs']
        for df_index, updated_df in enumerate(updated_dfs):
            column_name = st.session_state['recognised_column_names'][df_index]
            
            # Insert the new columns right after the original column
            col_index = final_df.columns.get_loc(column_name) + 1
            final_df.insert(col_index, column_name + "_najboljse_ujemanje", updated_df['najboljse_ujemanje'])
            final_df.insert(col_index + 1, column_name + "_identifikator", updated_df['identifikator'])


        st.write(f"CSV za izvox':")
        st.dataframe(final_df)  


        # Prenesi končno datoteko
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Prenesi končni CSV",
            data=csv,
            file_name="končni_podatki.csv",
            mime="text/csv",
        )
    else:
        st.warning("Ni končnih podatkov za prikaz!")                