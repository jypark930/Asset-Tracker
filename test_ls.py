import streamlit as st
from utils.local_auth import local_storage

st.write("Testing local storage...")

ls_data = local_storage("get_all", component_key="ls_get_all")

st.write("ls_data:", ls_data)

if st.button("Set dummy"):
    local_storage("set", "sb_refresh_token", "dummy_token", component_key="ls_set_dummy")
    st.rerun()

if st.button("Clear"):
    local_storage("remove", "sb_refresh_token", component_key="ls_remove_dummy")
    st.rerun()
