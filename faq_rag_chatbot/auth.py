from supabase import create_client
import streamlit as st

# ---------------- SUPABASE CLIENT ----------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- SIGN UP (REGISTER) ----------------
def sign_up(email: str, password: str):
    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        return response

    except Exception as e:
        return {"error": str(e)}

# ---------------- SIGN IN (LOGIN) ----------------
def sign_in(email: str, password: str):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        return response

    except Exception as e:
        return {"error": str(e)}

# ---------------- SIGN OUT (LOGOUT) ----------------
def sign_out():
    try:
        response = supabase.auth.sign_out()
        return response
    except Exception as e:
        return {"error": str(e)}

# ---------------- GET USER ----------------
def get_user():
    try:
        user = supabase.auth.get_user()
        return user
    except:
        return None
