"""
Case Number Manager
Manages sequential case numbers with JSON storage to prevent duplicates.
"""
import json
import os
import re
from pathlib import Path
from typing import Dict
from threading import Lock


class CaseNumberManager:
    """Manages case number generation and storage."""
    
    # Starting number for case sequences
    STARTING_NUMBER = 10673
    
    def __init__(self, storage_file: str = None):
        """
        Initialize the case number manager.
        
        Args:
            storage_file: Path to JSON storage file. Defaults to case_numbers.json in app directory.
        """
        if storage_file is None:
            # Default to app directory
            app_dir = Path(__file__).parent.parent
            storage_file = app_dir / "case_numbers.json"
        
        self.storage_file = Path(storage_file)
        self.lock = Lock()  # Thread safety for concurrent requests
        self._ensure_storage_exists()
    
    def _ensure_storage_exists(self):
        """Create storage file if it doesn't exist."""
        if not self.storage_file.exists():
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_data({
                "last_number": self.STARTING_NUMBER - 1,
                "case_registry": {}
            })
    
    def _load_data(self) -> Dict:
        """Load data from JSON storage."""
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # If file is corrupted or missing, reset it
            return {
                "last_number": self.STARTING_NUMBER - 1,
                "case_registry": {}
            }
    
    def _save_data(self, data: Dict):
        """Save data to JSON storage."""
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _generate_initials(self, client_name: str) -> str:
        """
        Generate initials from client name.
        
        Args:
            client_name: Full name of the client
            
        Returns:
            Initials (e.g., "John Doe" -> "JD")
        """
        if not client_name:
            return "XX"
        
        # Remove special characters and split by spaces
        clean_name = re.sub(r'[^a-zA-Z\s]', '', client_name)
        words = clean_name.strip().split()
        
        if not words:
            return "XX"
        
        # Take first letter of each word, max 2 letters
        if len(words) == 1:
            # Single word: use first two letters
            initials = words[0][:2].upper()
        else:
            # Multiple words: use first letter of first two words
            initials = ''.join([word[0].upper() for word in words[:2]])
        
        return initials
    
    def generate_case_number(self, client_name: str) -> str:
        """
        Generate a new case number for a client.
        
        Format: "[Initials] - SS - [Number]"
        Example: "JD - SS - 10673"
        
        Args:
            client_name: Full name of the client
            
        Returns:
            Formatted case number
        """
        with self.lock:
            # Load current data
            data = self._load_data()
            
            # Generate initials
            initials = self._generate_initials(client_name)
            
            # Get next number
            next_number = data["last_number"] + 1
            
            # Format case number
            case_number = f"{initials} - SS - {next_number}"
            
            # Update registry
            data["last_number"] = next_number
            data["case_registry"][case_number] = {
                "client_name": client_name,
                "timestamp": self._get_timestamp()
            }
            
            # Save updated data
            self._save_data(data)
            
            return case_number
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_case_info(self, case_number: str) -> Dict:
        """
        Get information about a specific case number.
        
        Args:
            case_number: The case number to lookup
            
        Returns:
            Dictionary with case information or None if not found
        """
        data = self._load_data()
        return data["case_registry"].get(case_number)
    
    def list_all_cases(self) -> Dict:
        """
        List all registered case numbers.
        
        Returns:
            Dictionary of all case numbers and their info
        """
        data = self._load_data()
        return data["case_registry"]
    
    def get_next_number(self) -> int:
        """
        Get the next number that will be assigned (without incrementing).
        
        Returns:
            Next case number
        """
        data = self._load_data()
        return data["last_number"] + 1
