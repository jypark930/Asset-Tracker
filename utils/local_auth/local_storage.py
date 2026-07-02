import os
import streamlit.components.v1 as components

_component_func = components.declare_component(
    "local_storage",
    path=os.path.dirname(os.path.abspath(__file__))
)

def local_storage(action: str, storage_key: str = None, value: str = None, component_key: str = None):
    """
    LocalStorage 인터페이스
    action: 'get', 'set', 'remove', 'get_all'
    """
    return _component_func(
        action=action, 
        storage_key=storage_key, 
        value=value, 
        key=component_key,
        default=None
    )
