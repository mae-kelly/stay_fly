import struct
from typing import List, Any, Optional

class SimpleABIDecoder:
    @staticmethod
    def decode_uint256(data: bytes) -> int:
        return int.from_bytes(data[:32], byteorder='big')
    
    @staticmethod
    def decode_address(data: bytes) -> str:
        return '0x' + data[12:32].hex()
    
    @staticmethod
    def decode_function_selector(data: bytes) -> str:
        return data[:4].hex()
    
    @staticmethod
    def extract_token_from_swap_data(calldata: bytes) -> Optional[str]:
        if len(calldata) < 4:
            return None
            
        method_id = calldata[:4].hex()
        
        if method_id in ['7ff36ab5', '18cbafe5']:
            if len(calldata) >= 196:
                try:
                    path_offset = 128
                    path_length_pos = path_offset + 32
                    if len(calldata) >= path_length_pos + 32:
                        token_pos = path_length_pos + 32 + 20
                        if len(calldata) >= token_pos + 20:
                            return '0x' + calldata[token_pos:token_pos + 20].hex()
                except:
                    pass
        
        elif method_id == '38ed1739':
            if len(calldata) >= 200:
                try:
                    path_offset = int.from_bytes(calldata[68:72], byteorder='big') + 4
                    if len(calldata) >= path_offset + 64:
                        return '0x' + calldata[path_offset + 44:path_offset + 64].hex()
                except:
                    pass
        
        return None

decoder = SimpleABIDecoder()
