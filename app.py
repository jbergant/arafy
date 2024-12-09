import streamlit as st
import pandas as pd
import Levenshtein
import time

def validate_words(input_string):
    """Preveri, da je vnos seznam besed, ločenih z vejicami, ki dovoljuje posebne znake in številke."""
    words = input_string.split(',')
    if all(word.strip() for word in words):  # Preveri, da vsaka beseda ni prazna
        return [word.strip() for word in words]
    else:
        return None

def process_csv(file, column, words):
    """Obdelaj CSV datoteko in izračunaj najboljše Levenshteinovo ujemanje za vsako besedo."""
    df = pd.read_csv(file)
    
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
    df['najboljše_ujemanje'], df['razmerje'], df['za_pregled'] = zip(
        *df[column].astype(str).apply(lambda x: find_best_match(x, words))
    )

    return df

# Streamlit Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["1. Vnos podatkov", "2. Ročna klasifikacija", "3. Združi rezultate", "4. Dodaj identifikatorje", "5. Rezultati"])

# Tab 1: Input Data
with tab1:
    st.header("1. Vnos podatkov")

    # File uploader
    uploaded_file = st.file_uploader("Naloži CSV", type="csv")

    # Input for column name
    column_name = st.text_input(
        "Vnesite ime stolpca za primerjavo:",
        placeholder="npr., Q1a_1_other"
    )

    if uploaded_file and column_name:
        try:
            # Read the file into a pandas DataFrame
            uploaded_file.seek(0)  # Reset file pointer before reading
            df = pd.read_csv(uploaded_file)

            if column_name in df.columns:
                # Extract unique words
                unique_words = df[column_name].dropna().unique()
                unique_words = [str(word).strip() for word in unique_words]
                unique_words_text = ", ".join(unique_words)

                # Display unique words
                st.write("Unikatne besede v izbranem stolpcu:")
                st.text_area(
                    "Unikatne besede (kopirajte, če je potrebno):",
                    value=unique_words_text,
                    height=150,
                    label_visibility="collapsed"
                )

                # Recommended words
                recommended_words = "telemach, telekom, a1, a1 slovenija, izimobil, t2, hofer, simobil, hot, bob, hot telekom, hofer telekom, t-2, mobitel, izi, spar mobil, telekom slovenije, izi mobil, tuš mobil, tuš, re do, hot mobil, siol, re:do"
                st.write("Priporočen seznam besed:")
                st.text_area(
                    "Priporočene besede:",
                    value=recommended_words,
                    height=150,
                    label_visibility="collapsed"
                )

            else:
                st.error(f"Stolpec '{column_name}' ni najden v naloženi CSV datoteki.")
        except pd.errors.EmptyDataError:
            st.error("CSV datoteka je prazna ali ima napačno obliko.")
        except Exception as e:
            st.error(f"Prišlo je do napake pri branju datoteke: {e}")

    st.subheader("Seznam besed za klasifikacijo:")
    word_input = st.text_area(
        "Vpiši seznam besed, ločenih z vejicami, za klasifikacijo:",
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
    if uploaded_file and word_input and column_name:
        try:
            uploaded_file.seek(0)  # Reset file pointer before processing again

            with st.spinner('Klasificiram podatke...'):
                processed_df = process_csv(uploaded_file, column_name, words)

            

            
            if processed_df is not None:
                st.session_state['processed_df'] = processed_df
                st.success("CSV datoteka uspešno obdelana!")
                st.write("Obdelani podatki:")
                st.dataframe(processed_df)
            else:
                st.error("Napaka pri obdelavi CSV datoteke.")
        except Exception as e:
            st.error(f"Prišlo je do napake pri obdelavi podatkov: {e}")


# Tab 2: Manual Classification
with tab2:
    st.header("2. Ročna klasifikacija")
    
    if 'processed_df' in st.session_state:
        df_to_check = st.session_state['processed_df'][st.session_state['processed_df']['za_pregled']]
        
        if not df_to_check.empty:
            st.write("Vrstice za pregled:")

            # Priprava možnosti za spustni seznam
            dropdown_options = ["neznano"] + words
            
            # Dodajanje spustnega seznama za "najboljše ujemanje"
            for index, row in df_to_check.iterrows():
                original_value = row[column_name]  # Prvotna vrednost za klasifikacijo
                df_to_check.at[index, 'najboljše_ujemanje'] = st.selectbox(
                    f"Uredi najboljše ujemanje za vrstico {index + 1} (Prvotna vrednost: {original_value}):",
                    options=dropdown_options,
                    index=dropdown_options.index(row['najboljše_ujemanje']) 
                    if row['najboljše_ujemanje'] in dropdown_options 
                    else dropdown_options.index("neznano")
                )
            
            # Shrani urejen DataFrame
            st.session_state['edited_df'] = df_to_check

        else:
            st.success("Ni vrstic za pregled!")
    else:
        st.warning("Najprej naloži in obdelaj podatke v zavihku '1. Vnos podatkov'.")

# Tab 3: Združi rezultate
with tab3:
    st.header("3. Združi rezultate")
    
    if 'processed_df' in st.session_state:
        # Privzeti slovar za preimenovanje
        default_switcher = {
            "telekom slovenije": "telekom",
            "a1 slovenija": "a1",
            "hofer": "hot",
            "hot mobil": "hot",
            "hot telekom": "hot",
            "hofer telekom": "hot",
            "izi mobil": "a1",
            "t-2": "t2",
            "mobitel": "telekom",
            "simobil": "a1",
            "tuš mobil": "telemach",
            "tuš": "telemach",
            "siol": "telekom",
        }
        
        # Pretvorimo slovar v DataFrame za urejanje
        switcher_df = pd.DataFrame(list(default_switcher.items()), columns=["Izvirno ime", "Novo ime"])
        
        # Uporabnikom omogočimo urejanje DataFrame-a
        edited_switcher_df = st.data_editor(
            switcher_df,
            num_rows="dynamic",  # Uporabniki lahko dodajo nove vrstice
            use_container_width=True
        )
        
        # Pretvorimo urejeni DataFrame nazaj v slovar
        user_switcher = dict(zip(edited_switcher_df["Izvirno ime"], edited_switcher_df["Novo ime"]))
        
        # Funkcija za preimenovanje z uporabniškim slovarjem
        def rename_best_match(name):
            if name is None or pd.isna(name):
                return name  # Če je vrednost None ali NaN, jo pustimo nespremenjeno
            return user_switcher.get(name.lower(), name)
        
        # Uporabi preimenovanje na stolpcu 'najboljše_ujemanje'
        st.session_state['processed_df']['najboljše_ujemanje'] = st.session_state['processed_df']['najboljše_ujemanje'].apply(rename_best_match)
        
        # Odstrani nepotrebna stolpca
        st.session_state['processed_df'] = st.session_state['processed_df'].drop(columns=["razmerje", "za_pregled"], errors="ignore")
        
        st.write("Posodobljeni podatki po združitvi rezultatov:")
        st.dataframe(st.session_state['processed_df'])
    else:
        st.warning("Najprej naloži in obdelaj podatke v zavihku '1. Vnos podatkov'.")

# Tab 4: Dodaj identifikatorje
with tab4:
    st.header("4. Dodaj identifikatorje")
    
    if 'processed_df' in st.session_state:
        # Privzeti slovar za identifikatorje
        default_identifiers = {
            "telekom": "1",
            "a1": "2",
            "telemach": "3",
            "t2": "4",
            "bob": "5",
            "hot": "6",
            "re:do": "7",
        }
        
        # Pretvorimo slovar v DataFrame za urejanje
        identifier_df = pd.DataFrame(list(default_identifiers.items()), columns=["Ime", "Identifikator"])
        
        # Uporabnikom omogočimo urejanje DataFrame-a
        edited_identifier_df = st.data_editor(
            identifier_df,
            num_rows="dynamic",  # Uporabniki lahko dodajo nove vrstice
            use_container_width=True
        )
        
        # Pretvorimo urejeni DataFrame nazaj v slovar
        user_identifiers = dict(zip(edited_identifier_df["Ime"], edited_identifier_df["Identifikator"]))
        
        # Funkcija za pridobitev identifikatorja
        def get_identifier(name):
            if name is None or pd.isna(name):
                return "8"  # Če je vrednost None ali NaN, privzeti identifikator
            return user_identifiers.get(name.lower(), "8")
        
        # Dodaj nov stolpec 'identifikator'
        st.session_state['processed_df']['identifikator'] = st.session_state['processed_df']['najboljše_ujemanje'].apply(get_identifier)
        
        st.write("Posodobljeni podatki z dodanimi identifikatorji:")
        st.dataframe(st.session_state['processed_df'])
    else:
        st.warning("Najprej naloži in obdelaj podatke v zavihku '1. Vnos podatkov'.")


with tab5:
    st.header("5. Rezultati")
    
    if 'edited_df' in st.session_state:
        st.write("Končni podatki po klasifikaciji:")
        final_df = st.session_state['processed_df']
        final_df.update(st.session_state['edited_df'])  # Update the original DataFrame with user edits
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