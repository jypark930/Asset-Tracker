import streamlit as st
import streamlit.components.v1 as components
import os

_component_func = components.declare_component('test_comp', path=os.path.abspath('utils/local_auth'))
st.write('Test Component')
val = _component_func(action='get', storage_key='test_key')
st.write('Component returned:', val)
