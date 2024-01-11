from .model_handler import ModelHandler
import json
from typing import Dict
from tensorflow.keras.models import Sequential
import numpy as np



class TensorflowModelHandler(ModelHandler):
    def __init__(self) -> None:
        super().__init__()
        
    def save_model(
        self, 
        model: Sequential,
        model_path: str = 'model.keras'
    ) -> str:
        self._model = model
        model.save(model_path)
        return model_path
    
    def save_dataset(
        self, 
        x_train: any,
        y_train: any,
        x_train_path: str = 'x_train.npy',
        y_train_path: str = 'y_train.npy'
    ) -> (str, str):
        np.save(x_train_path, x_train)
        np.save(y_train_path, y_train)
        return x_train_path, y_train_path
    
    
    def save_training_config(
        self, 
        training_config: Dict[str, any],
        training_config_path: str = 'training_config.json'
    ) -> str:
        with open(training_config_path, 'w') as json_file:
            json.dump(training_config, json_file)
        return training_config_path

    def load_trained_model(
        self,
        weights_path: str,
        history_path: str
    ) -> (any, Dict[str, any]):
        self._model.load_weights(weights_path)

        with open(history_path, 'r') as json_file:
            history_data = json.load(json_file)

        return self._model, history_data