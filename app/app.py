import streamlit as st
from PIL import Image
import io
import pillow_avif
import time
import re
import ast


from backend.config import Config
from backend.azure_storage import AzureStorageHandler
from backend.image_processor import ImageProcessor
from backend.databricks_client import DatabricksClient

databricks_client = DatabricksClient()

#Time Format
def format_duration(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes} min {secs} sec"
    else:
        return f"{secs} sec"


# Page configuration
st.set_page_config(
    page_title="Visual Product Search POC",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state for search results
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False
if 'search_results' not in st.session_state:
    st.session_state.search_results = None

# Initialize Azure connection
@st.cache_resource
def init_azure_storage():
    """Initialize Azure Storage connection"""
    try:
        Config.validate()
        storage_handler = AzureStorageHandler()
        if storage_handler.connect():
            return storage_handler
        else:
            return None
    except Exception as e:
        st.error(f"Configuration error: {str(e)}")
        return None

# Initialize storage handler
storage_handler = init_azure_storage()

# Custom CSS for professional styling
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #0066cc;
        color: white;
        font-weight: 500;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        border: none;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #0052a3;
    }
    h1 {
        color: #1a1a1a;
        font-weight: 600;
    }
    h3 {
        color: #333333;
        font-weight: 500;
    }
    .product-card {
        border: 1px solid #e0e0e0;
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: box-shadow 0.3s;
    }
    .product-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .product-image-placeholder {
        height: 120px;
        background-color: #f5f5f5;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 12px;
        border-radius: 4px;
        color: #999999;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
st.title("Visual Product Search POC")
st.markdown("**Multimodal AI-powered product discovery system**")

# Show Azure connection status
if storage_handler:
    st.success("Connected to Azure Storage")
else:
    st.warning("Azure Storage not configured. Please set up your .env file.")

st.markdown("---")

# Create two columns for search options
col1, col2 = st.columns(2, gap="large")

# Image Search Column
with col1:
    st.markdown("### Image-Based Search")
    st.markdown("Upload a product image to find visually similar items")
    
    uploaded_file = st.file_uploader(
    "Upload product image (max 10MB)",
    type=['jpg','jpeg','png'],
    key="image_uploader",
    help="Accepted: JPG, PNG, AVIF."
)


    
    if uploaded_file is not None:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        st.info(f"File: {uploaded_file.name}, Size: {file_size_mb:.2f}MB")
        # Display the uploaded image
        # image = Image.open(uploaded_file)
        # st.image(image, caption='Uploaded Image', use_column_width=True)
        try:
            image = Image.open(uploaded_file)
            st.image(image, caption='Uploaded Image', use_column_width=250)
        except Exception as e:
            st.error(f"Cannot open file as image: {e}")

        
        # Search button for image
        if st.button("Search Similar Products", key="img_search_btn", type="primary"):
            search_start_time = time.time()
            with st.spinner("Processing and uploading image..."):
                try:
                    # Validate image
                    is_valid, error_msg = ImageProcessor.validate_image(uploaded_file)
                    if not is_valid:
                        st.error(error_msg)
                    else:
                        # Reset file position
                        uploaded_file.seek(0)
                        
                        # Process the image
                        processed_image = ImageProcessor.process_image(uploaded_file)
                        
                        # Upload to Azure if connected
                        blob_url = None
                        if storage_handler:
                            blob_url = storage_handler.upload_image(
                                processed_image,

                                uploaded_file.name,
                                ImageProcessor.get_image_metadata(uploaded_file)
                            )
                            
                            if blob_url:
                                st.success("Image uploaded to Azure Storage")
                                with st.expander("Upload Details"):
                                    st.text(f"Blob URL: {blob_url}")
                                try:
                                    run_id = databricks_client.run_job()
                                    st.info(f"Databricks job triggered successfully. Run ID: {run_id}")
                                    timeout_seconds = 1800
                                    poll_interval = 30
                                    start_time = time.time()

                                    while True:
                                        status = databricks_client.get_run_status(run_id)
                                        life_cycle_state = status['state']['life_cycle_state']
                                        if life_cycle_state in ('TERMINATED', 'SKIPPED'):
                                            break
                                        if time.time() - start_time > timeout_seconds:
                                            st.error("Databricks job timed out")
                                            break
                                        time.sleep(poll_interval)
                                        
                                    if life_cycle_state == 'TERMINATED':
                                        output = databricks_client.get_run_output(run_id)
                                        notebook_result = output.get('notebook_output', {}).get('result')
                                        st.success("Databricks job completed")
                                        st.text(f"Output:\n{notebook_result}")

                                        try:
                                            parsed_output = ast.literal_eval(notebook_result)
                                            top_results = parsed_output.get("Top 5 Similar results", [])
                                        except Exception as e:
                                            st.error(f"Failed to parse Databricks output: {e}")
                                            top_results = []

                                        search_results = []
                                        sas_token = Config.AZURE_SAS_TOKEN.strip("?")
                                        for item in top_results:
                                            # {
                                            #   'productName': '...',
                                            #   'modelRefNo': 'RTxxxxx',
                                            #   'image_path': 'images/RTXXXXXX/HL.jpg',
                                            #   'price': '00000',
                                            #   'largeUrl': '//images.samsung.com/is/image/...'
                                            # }
                                            product_name = item.get("productName") or "Product"
                                            model_ref = item.get("modelRefNo") or ""
                                            large_url = item.get("largeUrl")
                                            if large_url:
                                            #as per samsung avif
                                                image_url = f"https:{large_url}"
                                            else:
                                                #fall back - uses blob storage
                                                image_path = item.get("image_path", "")
                                                image_url = (
                                                    f"https://{Config.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/"
                                                    f"{Config.AZURE_STORAGE_CONTAINER_NAME}/{image_path}"
                                                )
                                                if sas_token:
                                                    image_url = f"{image_url}?{sas_token}"
                                            raw_price = item.get("price")
                                            price_display = f"₹{raw_price}" if raw_price not in (None, "", "None") else "Out of Stock"

                                            search_results.append({
                                                "productName": product_name,
                                                "modelRefNo": model_ref,
                                                "price": price_display,
                                                "image": image_url,
                                            })
                                        if search_results:
                                            st.session_state.search_results = search_results
                                        else:
                                            st.warning("No results parsed from Databricks output")
                                    else:
                                        st.error(f"Job ended with state: {life_cycle_state}")
                                except Exception as e:
                                    st.error(f"Failed to trigger Databricks job: {e}")
                        
                        # Set search performed flag
                        st.session_state.search_performed = True
                        st.session_state.search_type = "image"
                        if blob_url:
                            st.session_state.blob_url = blob_url
                        elapsed_time = time.time() - search_start_time
                        st.session_state.search_time = elapsed_time
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    elapsed_time = time.time() - search_start_time
                    st.session_state.search_time = elapsed_time
        


# # Text Search Column
# with col2:
#     st.markdown("### Text-Based Search")
#     st.markdown("Describe the product you're looking for")
    
#     text_query = st.text_area(
#         "Product description",
#         height=150,
#         placeholder="Example: Red running shoes with white soles, or Vintage leather jacket with brass buttons",
#         key="text_input"
#     )
    
#     # Search button for text
#     if st.button("Search Products", key="text_search_btn", disabled=not text_query, type="primary"):
#         if text_query:
#             with st.spinner("Searching product catalog..."):
#                 # Simulate backend call - replace with actual API call
#                 import time
#                 time.sleep(2)  # Simulate processing time
                
#                 # Set search performed flag
#                 st.session_state.search_performed = True
#                 st.session_state.search_type = "text"
#                 st.session_state.search_query = text_query
                
#                 # Placeholder for actual search results
#                 st.session_state.search_results = [
#                     {"name": f"Product {i+1}", "similarity": 95-i*5, "id": f"PRD-{1000+i}"} 
#                     for i in range(5)
#                 ]
                
#                 st.success("Search complete")

# Results Section - Only show if search was performed
if st.session_state.search_performed and st.session_state.search_results:
    st.markdown("---")
    st.markdown("### Search Results")
    
    # Show what was searched
    if st.session_state.search_type == "text":
        st.markdown(f"**Query:** {st.session_state.search_query}")
    else:
        st.markdown("**Query Type:** Image-based search")
    
    # Display results count and metrics
    col_metric1, col_metric2, col_metric3 = st.columns(3)
    with col_metric1:
        st.metric("Results Found", len(st.session_state.search_results))
    # with col_metric2:
    #     search_time = st.session_state.get("search_time", None)
    #     if search_time is not None:
    #         st.metric("Search Time", format_duration(search_time))
    #     else:
    #         st.metric("Search Time", "-")
    # with col_metric3:
    #     st.metric("Confidence", "-")
    
    # Display results grid
    st.markdown("#### Top Matches")
    
    cols = st.columns(5)
    # for i, (col, result) in enumerate(zip(cols, st.session_state.search_results)):
    #     with col:
    #         st.markdown(f"""
    #             <div class="product-card">
    #                 <div class="product-image-placeholder">
    #                     Image {i+1}
    #                 </div>
    #                 <p style="margin: 0; font-size: 14px; font-weight: 500; color: #333;">{result['name']}</p>
    #                 <p style="margin: 4px 0; font-size: 12px; color: #666;">ID: {result['id']}</p>
    #                 <p style="margin: 0; font-size: 13px; color: #0066cc; font-weight: 500;">Match: {result['similarity']}%</p>
    #             </div>
    #             """, unsafe_allow_html=True)
    
    # # Add action buttons
    # st.markdown("")
    # col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
    # with col_btn1:
    #     if st.button("New Search", key="new_search_btn"):
    #         st.session_state.search_performed = False
    #         st.session_state.search_results = None
    #         st.rerun()
    # with col_btn2:
    #     st.button("Export Results", key="export_btn", disabled=True)
    for i, (col, result) in enumerate(zip(cols, st.session_state.search_results)):
        with col:
            image_html = (
                f"<img src='{result.get('image')}' "
                f"alt='{result.get('productName')}' "
                f"style='max-width:100%; max-height:120px; border-radius:4px;'/>"
                if result.get("image") else
                "<div class='product-image-placeholder'>No image</div>"
            )

            price_text = (
                f"Price: {result.get('price')}"
                if result.get('price') != "Out of Stock"
                else "Out of Stock"
            )

            st.markdown(f"""
                <div class="product-card">
                    {image_html}
                    <p style="margin: 0; font-size: 14px; font-weight: 500; color: #333;">
                        {result.get('productName')}
                    </p>
                    <p style="margin: 4px 0; font-size: 12px; color: #666;">
                        ModelRef: {result.get('modelRefNo')}
                    </p>
                    <p style="margin: 0; font-size: 13px; color: #0066cc; font-weight: 500;">
                        {price_text}
                    </p>
                </div>
            """, unsafe_allow_html=True)
    
    # Add action buttons
    st.markdown("")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])

    with col_btn1:
        if st.button("New Search", key="new_search_btn"):
            st.session_state.search_performed = False
            st.session_state.search_results = None
            st.rerun()

    with col_btn2:
        if st.session_state.search_results:
            import pandas as pd
            df = pd.DataFrame(st.session_state.search_results)
            st.download_button(
                label="Export Results",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name="search_results.csv",
                mime="text/csv",
                key="export_btn"
            )


# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666666; font-size: 14px;">
        Visual Product Search POC | Version 1.0 | Powered by Multimodal AI
    </div>
    """, 
    unsafe_allow_html=True
)