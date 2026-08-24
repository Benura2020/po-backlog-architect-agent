from typing import Protocol, List, Optional, Dict, Any


class DocumentStore(Protocol):
    def get_document(self, doc_name: str) -> Optional[str]: ...
    def list_sections(self) -> List[Dict[str, Any]]: ...


class MockDocumentStore:
    def __init__(self, sections: List[Dict[str, Any]]):
        self.sections = sections

    def get_document(self, doc_name: str) -> Optional[str]:
        return "\n\n".join([f"### {s['title']}\n{s['content']}" for s in self.sections])

    def list_sections(self) -> List[Dict[str, Any]]:
        return self.sections
