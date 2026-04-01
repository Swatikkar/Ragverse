from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader, CSVLoader, UnstructuredExcelLoader,UnstructuredPowerPointLoader
from config import UPLOAD_DIR
import os

LOADERS = {
    ".pdf": PyMuPDFLoader,
    ".docx": Docx2txtLoader,
    ".csv": CSVLoader,
    ".xlsx": UnstructuredExcelLoader,
    ".pptx": UnstructuredPowerPointLoader
}

def load_document(file_path: str,doc_id: str) -> list:
    ext = os.path.splitext(file_path)[-1].lower()

    if ext not in LOADERS:
        raise ValueError(f"Unsupported file type: {ext}")

    loader = LOADERS[ext](file_path)
    pages = loader.load()

    for i, page in enumerate(pages):
        page.metadata["doc_id"] = doc_id
        page.metadata["doc_name"] = os.path.basename(file_path)  # add explicitly
        page.metadata["file_type"] = ext

        if ext == ".pdf":
            page.metadata["page_num"] = page.metadata.get("page", i) + 1  # fix 0-based
        elif ext in [".csv", ".xlsx"]:
            page.metadata["page_num"] = None
            page.metadata["row_index"] = i
        elif ext == ".docx":
            page.metadata["page_num"] = None
            page.metadata["section_index"] = i
        elif ext == ".pptx":
            page.metadata["page_num"] = None
            page.metadata["slide_index"] = i

        page.metadata["source"] = os.path.basename(file_path)

    print(f"Page metadata: {page.metadata}")

    return pages