from typing import Dict


class ModelHandler:
    def __init__(
        self
    ) -> None:
        self._model = None
    
    def save_model(
        self, 
        model: any,
        model_path: str
    ) -> str:
        pass
    
    def save_dataset(
        self, 
        x_train: any,
        y_train: any,
        x_train_path: str,
        y_train_path: str
    ) -> (str, str):
        pass
    
    def save_training_config(
        self, 
        training_config: Dict[str, any],
        training_config_path: str
    ) -> str:
        pass
    
    def load_trained_model(
        self,
        weights_path: str,
        history_path: str
    ) -> (any, Dict[str, any]):
         pass   
    
    