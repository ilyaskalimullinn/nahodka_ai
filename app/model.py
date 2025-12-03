from typing import List
from abc import ABC
import os

import torch
import open_clip


class ModelService(ABC):
    def encode_text(text: str) -> List[int]:
        pass


class OpenClipModelService(ModelService):
    def __init__(self, model_path_or_name: str):
        super().__init__()
        self.model_path_or_name = model_path_or_name

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model, self.preprocess = open_clip.create_model_from_pretrained(
            model_path_or_name, device=self.device
        )
        self.tokenizer = open_clip.get_tokenizer(model_path_or_name)

    def encode_text(self, text: str) -> List[int]:
        tensor = self.tokenizer([text]).to(self.device)
        embeddings = self.model.encode_text(tensor).detach().cpu()
        embeddings = embeddings.tolist()[0]
        return embeddings


model_service = OpenClipModelService(
    model_path_or_name=os.environ.get("MODEL_PATH_OR_NAME")
)
