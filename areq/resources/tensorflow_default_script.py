import json
import numpy as np
from typing import Dict
from tensorflow.keras.models import load_model

model = load_model('model.keras')

with open('training_config.json', 'r') as json_file:
    training_config = json.load(json_file)

x_train = np.load('x_train.npy')
y_train = np.load('y_train.npy')

model.compile(
    optimizer=training_config['optimizer'],
    loss=training_config['loss'],
    metrics=training_config['metrics']
)

history = model.fit(
    x_train, y_train,
    batch_size=training_config['batch_size'],
    epochs=training_config['epochs'],
    validation_split=0.2
)

model.save_weights('weights.h5')

with open('history.json', 'w') as json_file:
    json.dump(history.history, json_file)
