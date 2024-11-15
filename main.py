##This code has been sourced from Github:https://github.com/nicknochnack/FaceDetection##
##We have changed the dataset , and parameters to run the code according to our implementation , have replaced few deprecated functions. The plotting has been done using a simple matplotlib program##

import albumentations as alb
import cv2
import os
import json
import time
import uuid
import numpy as np
from matplotlib import pyplot as plt
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Conv2D, Dense, GlobalMaxPooling2D
from tensorflow.keras.applications import VGG16
from tensorflow.keras.models import load_model

#Setting the image path and collecting the images
IMAGES_PATH = os.path.join('data','images')
number_images = 30

cap = cv2.VideoCapture(0)
for imgnum in range(number_images):
    print('Collecting image {}'.format(imgnum))
    ret, frame = cap.read()
    imgname = os.path.join(IMAGES_PATH,f'{str(uuid.uuid1())}.jpg')
    cv2.imwrite(imgname, frame)
    cv2.imshow('frame', frame)
    time.sleep(0.5)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()

#!labelme ## This command was used to open the annotation program using command line

#Loading images in the TF pipeline
images = tf.data.Dataset.list_files('data\\images\\*.jpg')
images.as_numpy_iterator().next()
def load_image(x):
    byte_img = tf.io.read_file(x)
    img = tf.io.decode_jpeg(byte_img)
    return img
images = images.map(load_image)
print(images.as_numpy_iterator().next())

##Then the data was split manually into train , test , validate

##moving the matching labels to the respective image folders
for folder in ['train', 'test', 'val']:
    for file in os.listdir(os.path.join('data', folder, 'images')):

        filename = file.split('.')[0] + '.json'
        existing_filepath = os.path.join('data', 'labels', filename)
        if os.path.exists(existing_filepath):
            new_filepath = os.path.join('data', folder, 'labels', filename)
            os.replace(existing_filepath, new_filepath)


#augmentation using albumentation library


augmentor = alb.Compose([alb.RandomCrop(width=450, height=450),
                         alb.HorizontalFlip(p=0.5),
                         alb.RandomBrightnessContrast(p=0.2),
                         alb.RandomGamma(p=0.2),
                         alb.RGBShift(p=0.2),
                         alb.VerticalFlip(p=0.5)],
                       bbox_params=alb.BboxParams(format='albumentations',
                                                  label_fields=['class_labels']))

img = cv2.imread(os.path.join('data','train', 'images','d96b1b9a-745c-11ed-aeb1-940853b44c8c.jpg'))
with open(os.path.join('data', 'train', 'labels', 'd96b1b9a-745c-11ed-aeb1-940853b44c8c.json'), 'r') as f:
    label = json.load(f)

#print(label['shapes'][0]['points'])
#
##Rescaling the images
coords = [0,0,0,0]
coords[0] = label['shapes'][0]['points'][0][0]
coords[1] = label['shapes'][0]['points'][0][1]
coords[2] = label['shapes'][0]['points'][1][0]
coords[3] = label['shapes'][0]['points'][1][1]

#print(coords)

coords = list(np.divide(coords, [640,480,640,480]))

##Applying Augmentation
augmented = augmentor(image=img, bboxes=[coords], class_labels=['face'])
augmented['bboxes'][0][2:]
augmented['bboxes']
cv2.rectangle(augmented['image'],
              tuple(np.multiply(augmented['bboxes'][0][:2], [450,450]).astype(int)),
              tuple(np.multiply(augmented['bboxes'][0][2:], [450,450]).astype(int)),
                    (255,0,0), 2)

#plt.imshow(augmented['image'])

##Augmentation Pipeline
for partition in ['train','test','val']:
    for image in os.listdir(os.path.join('data', partition, 'images')):
        img = cv2.imread(os.path.join('data', partition, 'images', image))
#
        coords = [0,0,0.00001,0.00001]
        label_path = os.path.join('data', partition, 'labels', f'{image.split(".")[0]}.json')
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                label = json.load(f)
#
            coords[0] = label['shapes'][0]['points'][0][0]
            coords[1] = label['shapes'][0]['points'][0][1]
            coords[2] = label['shapes'][0]['points'][1][0]
            coords[3] = label['shapes'][0]['points'][1][1]
            coords = list(np.divide(coords, [640,480,640,480]))
#
        try:
            for x in range(3):
                augmented = augmentor(image=img, bboxes=[coords], class_labels=['face'])
                cv2.imwrite(os.path.join('aug_data', partition, 'images', f'{image.split(".")[0]}.{x}.jpg'), augmented['image'])
#
                annotation = {}
                annotation['image'] = image
#
                if os.path.exists(label_path):
                    if len(augmented['bboxes']) == 0:
                        annotation['bbox'] = [0,0,0,0]
                        annotation['class'] = 0
                    else:
                        annotation['bbox'] = augmented['bboxes'][0]
                        annotation['class'] = 1
                else:
                    annotation['bbox'] = [0,0,0,0]
                    annotation['class'] = 0
#
#
                with open(os.path.join('aug_data', partition, 'labels', f'{image.split(".")[0]}.{x}.json'), 'w') as f:
                    json.dump(annotation, f)
#
        except Exception as e:
            print(e)


#Loading the Augmented Results to TF Dataset
#Image Loading function
def load_image(x):
     byte_img = tf.io.read_file(x)
     img = tf.io.decode_jpeg(byte_img)
     return img

train_images = tf.data.Dataset.list_files('aug_data\\train\\images\\*.jpg', shuffle=False)
train_images = train_images.map(load_image)
train_images = train_images.map(lambda x: tf.image.resize(x, (120,120)))
train_images = train_images.map(lambda x: x/255)

test_images = tf.data.Dataset.list_files('aug_data\\test\\images\\*.jpg', shuffle=False)
test_images = test_images.map(load_image)
test_images = test_images.map(lambda x: tf.image.resize(x, (120,120)))
test_images = test_images.map(lambda x: x/255)
#
val_images = tf.data.Dataset.list_files('aug_data\\val\\images\\*.jpg', shuffle=False)
val_images = val_images.map(load_image)
val_images = val_images.map(lambda x: tf.image.resize(x, (120,120)))
val_images = val_images.map(lambda x: x/255)

#print(train_images.as_numpy_iterator().next())

##Label loading function
def load_labels(label_path):
    with open(label_path.numpy(), 'r', encoding="utf-8") as f:
        label = json.load(f)

    return [label['class']], label['bbox']

train_labels = tf.data.Dataset.list_files('aug_data\\train\\labels\\*.json', shuffle=False)
train_labels = train_labels.map(lambda x: tf.py_function(load_labels, [x], [tf.uint8, tf.float16]))
#
test_labels = tf.data.Dataset.list_files('aug_data\\test\\labels\\*.json', shuffle=False)
test_labels = test_labels.map(lambda x: tf.py_function(load_labels, [x], [tf.uint8, tf.float16]))
#
val_labels = tf.data.Dataset.list_files('aug_data\\val\\labels\\*.json', shuffle=False)
val_labels = val_labels.map(lambda x: tf.py_function(load_labels, [x], [tf.uint8, tf.float16]))
#
#print(train_labels.as_numpy_iterator().next())

#print(len(train_images), len(train_labels), len(test_images), len(test_labels), len(val_images), len(val_labels))
##Combining the final dataset , images + labels
train = tf.data.Dataset.zip((train_images, train_labels))
train = train.shuffle(30)
train = train.batch(2)
train = train.prefetch(1)
#
test = tf.data.Dataset.zip((test_images, test_labels))
test = test.shuffle(12)
test = test.batch(2)
test = test.prefetch(1)
#
val = tf.data.Dataset.zip((val_images, val_labels))
val = val.shuffle(10)
val = val.batch(2)
val = val.prefetch(1)

#print(train.as_numpy_iterator().next()[1])
#Viewing sample images in the dataset
# data_samples = train.as_numpy_iterator()
# res = data_samples.next()
# #print(len(res))
# fig, ax = plt.subplots(ncols=2, figsize=(20, 20))
# for idx in range(2):
#     sample_image = res[0][idx]
#     sample_coords = res[1][1][idx]
#
#     cv2.rectangle(sample_image,
#                    tuple(np.multiply(sample_coords[:2], [120, 120]).astype(int)),
#                    tuple(np.multiply(sample_coords[2:], [120, 120]).astype(int)),
#                    (255, 0, 0), 2)
#
#     ax[idx].imshow(sample_image)

##Build deep learning using the Functional API

#Import Layers and Base Networks



vgg = VGG16(include_top=False)
#print(vgg.summary())

#Build instance of a neural network
def build_model():
    input_layer = Input(shape=(120, 120, 3))
# #
    vgg = VGG16(include_top=False)(input_layer)
# #
# #     # Classification Model
    f1 = GlobalMaxPooling2D()(vgg)
    class1 = Dense(2048, activation='relu')(f1)
    class2 = Dense(1, activation='sigmoid')(class1)
#
#      # Bounding box model
    f2 = GlobalMaxPooling2D()(vgg)
    regress1 = Dense(2048, activation='relu')(f2)
    regress2 = Dense(4, activation='sigmoid')(regress1)
#
    facetracker = Model(inputs=input_layer, outputs=[class2, regress2])
    return facetracker

#Test out Neural Network

facetracker = build_model()
 #print(facetracker.summary())
X, y = train.as_numpy_iterator().next()
classes, coords = facetracker.predict(X)
# print(X.shape,classes,coords)
#print(train.as_numpy_iterator().next()[1])

#Define Losses and Optimizers

batches_per_epoch = len(train)

opt = tf.keras.optimizers.Adam(learning_rate=0.0001)


#Create Localization Loss and Classification Loss
def localization_loss(y_true, yhat):
    delta_coord = tf.reduce_sum(tf.square(y_true[:, :2] - yhat[:, :2]))

    h_true = y_true[:, 3] - y_true[:, 1]
    w_true = y_true[:, 2] - y_true[:, 0]

    h_pred = yhat[:, 3] - yhat[:, 1]
    w_pred = yhat[:, 2] - yhat[:, 0]

    delta_size = tf.reduce_sum(tf.square(w_true - w_pred) + tf.square(h_true - h_pred))

    return delta_coord + delta_size

classloss = tf.keras.losses.BinaryCrossentropy()
regressloss = localization_loss

#Test out loss Metrics


# print('Loss Metrics =',localization_loss(y[1], coords).numpy())
#
# print('class loss =',classloss(y[0], classes).numpy())
#
# print('regress loss =',regressloss(y[1], coords).numpy())

#Train Neural Networks

class FaceTracker(Model):
    def __init__(self, eyetracker, **kwargs):
        super().__init__(**kwargs)
        self.model = eyetracker

    def compile(self, opt, classloss, localizationloss, **kwargs):
        super().compile(**kwargs)
        self.closs = classloss
        self.lloss = localizationloss
        self.opt = opt

    def train_step(self, batch, **kwargs):
        X, y = batch

        with tf.GradientTape() as tape:
            classes, coords = self.model(X, training=True)

            batch_classloss = self.closs(y[0], classes)
            batch_localizationloss = self.lloss(tf.cast(y[1], tf.float32), coords)

            total_loss = batch_localizationloss + 0.5 * batch_classloss

            grad = tape.gradient(total_loss, self.model.trainable_variables)

        opt.apply_gradients(zip(grad, self.model.trainable_variables))

        return {"total_loss": total_loss, "class_loss": batch_classloss, "regress_loss": batch_localizationloss}

    def test_step(self, batch, **kwargs):
        X, y = batch

        classes, coords = self.model(X, training=False)

        batch_classloss = self.closs(y[0], classes)
        batch_localizationloss = self.lloss(tf.cast(y[1], tf.float32), coords)
        total_loss = batch_localizationloss + 0.5 * batch_classloss

        return {"total_loss": total_loss, "class_loss": batch_classloss, "regress_loss": batch_localizationloss}

    def call(self, X, **kwargs):
        return self.model(X, **kwargs)

model = FaceTracker(facetracker)

model.compile(opt, classloss, regressloss)

# #Train
logdir='logs'
tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=logdir)
hist = model.fit(train, epochs=40, validation_data=val, callbacks=[tensorboard_callback])



##Making Predictions

test_data = test.as_numpy_iterator()
test_sample = test_data.next()
print(len(test_sample))
yhat = facetracker.predict(test_sample[0])
fig, ax = plt.subplots(ncols=2, figsize=(20, 20))
for idx in range(2):
    sample_image = test_sample[0][idx]
    sample_coords = yhat[1][idx]
    print('Threshold',yhat[0][idx])
    if yhat[0][idx] > 0.7:
        cv2.rectangle(sample_image,
                      tuple(np.multiply(sample_coords[:2], [120, 120]).astype(int)),
                      tuple(np.multiply(sample_coords[2:], [120, 120]).astype(int)),
                            (255, 0, 0), 2)
#
    ax[idx].imshow(sample_image)

facetracker.save('facetracker.h5')
facetracker = load_model('facetracker.h5')

#Real Time Detection
cap = cv2.VideoCapture(2)
while cap.isOpened():
    _, frame = cap.read()
    frame = frame[50:500, 50:500, :]

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resized = tf.image.resize(rgb, (120, 120))

    yhat = facetracker.predict(np.expand_dims(resized / 255, 0))
    sample_coords = yhat[1][0]

    if yhat[0] > 0.5:
        # Controls the main rectangle
        cv2.rectangle(frame,
                      tuple(np.multiply(sample_coords[:2], [450, 450]).astype(int)),
                      tuple(np.multiply(sample_coords[2:], [450, 450]).astype(int)),
                      (255, 0, 0), 2)
        # Controls the label rectangle
        cv2.rectangle(frame,
                      tuple(np.add(np.multiply(sample_coords[:2], [450, 450]).astype(int),
                                   [0, -30])),
                      tuple(np.add(np.multiply(sample_coords[:2], [450, 450]).astype(int),
                                   [80, 0])),
                      (255, 0, 0), -1)

        # Controls the text rendered
        cv2.putText(frame, 'face', tuple(np.add(np.multiply(sample_coords[:2], [450, 450]).astype(int),
                                                [0, -5])),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    cv2.imshow('EyeTrack', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()

plt.show()


##The code used for plotting the losses##
# import matplotlib.pyplot as plt
# import numpy as np
#
# class_loss = [0.4804 , 0.2871 , 0.1571 , 0.1116 , 0.0375 , 0.0139 , 0.0098 , 0.0168 , 0.0034 , 0.0019 , 0.0143 , 0.0068 , 0.0020 , 0.0023 , 9.1868e-04 , 0.0023 , 6.8777e-04 , 6.1136e-04, 6.1734e-04 , 3.8145e-04 , 3.8789e-04 , 1.8992e-04 ,1.5892e-04 , 2.6469e-04 , 6.3849e-04 , 3.1186e-04 , 2.9677e-04 , 5.2862e-04 , 4.9696e-04 , 3.5637e-04 , 2.0718e-04 , 8.8890e-05 , 7.3595e-05 , 8.1090e-05 , 9.4591e-05 , 7.6219e-05 , 9.6306e-05 , 5.9682e-05 , 4.8357e-05 , 4.6231e-05]
# total_loss = [0.6241 , 0.3859 , 0.2665 , 0.1789 , 0.1360 ,0.0706 , 0.1081 , 0.0602 , 0.0356 , 0.0504 , 0.1078 , 0.0506 , 0.0321 , 0.0290 , 0.0301 , 0.0158 , 0.0088 , 0.0105 , 0.0110 , 0.0070 , 0.0037 , 0.034 ,0.063, 0.0103 , 0.0093 , 0.0064 , 0.0114 , 0.0213 , 0.0115 , 0.0039 , 0.0023 , 0.0034 , 0.0047 , 0.0029 , 0.0028 , 0.0016 , 0.0011 , 0.0011 , 0.0014 , 0.0013]
# #total_loss = [0.6241 , 0.3859 , 0.2665 , 0.1789 , 0.1360 ,0.0706 , 0.1081 , 0.0602 , 0.0356 , 0.0504 , 0.1078 , 0.0506 , 0.0321 , 0.0290 , 0.0301 , 0.0158 , 0.0088 , 0.0105 , 0.0110 , 0.0070 , 0.0037 , 0.034 , 0.0103 , 0.0093 , 0.0064 , 0.0114 , 0.0213 , 0.0115 , 0.0039 , 0.0023 , 0.0034 , 0.0047 , 0.0029 , 0.0028 , 0.0016 , 0.0011 , 0.0011 , 0.0014 , 0.0013]
# #class_loss = [0.4804 , 0.2871 , 0.1571 , 0.1116 , 0.0375 , 0.0139 , 0.0098 , 0.0168 , 0.0034 , 0.0019 , 0.0143 , 0.0068 , 0.0020 , 0.0023 , 9.1868e-04 , 0.0023 , 6.8777e-04 , 6.1136e-04, 6.1734e-04 , 3.8145e-04 , 3.8789e-04 , 1.8992e-04 , 2.6469e-04 , 6.3849e-04 , 3.1186e-04 , 2.9677e-04 , 5.2862e-04 , 4.9696e-04 , 3.5637e-04 , 2.0718e-04 , 8.8890e-05 , 7.3595e-05 , 8.1090e-05 , 9.4591e-05 , 7.6219e-05 , 9.6306e-05 , 5.9682e-05 , 4.8357e-05 , 4.6231e-05]
# reg_loss =[0.3839 , 0.2423 , 0.1879 , 0.1231 , 0.1173 , 0.0637 , 0.1032 , 0.0518 , 0.0339 , 0.0495 , 0.1007 , 0.0471 , 0.0311 , 0.0278 , 0.0296 , 0.0146 , 0.0085 , 0.0102 , 0.0107 , 0.0068 , 0.0035 , 0.0033 , 0.0062 , 0.0102 , 0.0090 , 0.0063 , 0.0112 , 0.0211 , 0.0112 , 0.0037 , 0.0022 , 0.0034 , 0.0047 , 0.0029 , 0.0027 , 0.0015 , 0.0010 , 0.0010 , 0.0014 , 0.0013]
#
# val_totalL = [0.3033 , 0.3225 , 0.1686 , 0.0894 , 0.1297 , 0.2099 , 0.1218 , 0.1011 , 0.1758 , 0.0832 , 0.2097 , 0.1046 , 0.1200 , 0.1680 , 0.0776 , 0.0926 , 0.0747 , 0.1936 , 0.1257 , 0.1368 , 0.0554 , 0.0491 , 0.1211 , 0.1103, 0.1005 , 0.0510 , 0.1273 , 0.1567 , 0.0414 , 0.1688 , 0.1018 , 0.0660 , 0.0845 , 0.0522 , 0.0967 , 0.1370 , 0.0521 , 0.0864 , 0.1298 , 0.1179]
# val_classL = [0.0955 , 0.0812 , 0.0061 , 0.0046 , 0.0065 , 8.3539e-04 , 0.0067 , 0.0011 , 0.0032 , 0.0086 , 0.0421 , 7.6296e-04 , 0.0029 , 0.0030 , 0.0029 , 0.0018 , 7.8662e-04 , 0.0037 , 0.0011 , 0.0022 , 7.2784e-04, 1.4560e-04 , 0.0011 , 0.016 , 0.0013 , 3.9981e-04 , 0.0026 , 0.0041 , 4.7555e-04 , 0.0016 , 7.7320e-04 , 1.8885e-04 , 6.3300e-04 , 2.7334e-04 , 4.5072e-04 , 0.0010 , 1.4029e-04 , 3.5415e-04 , 2.8884e-04 , 4.7969e-04 ]
# val_regressL = [0.2556 , 0.2819 , 0.1656 , 0.0871 , 0.1264 , 0.2095 , 0.1185 , 0.1006 , 0.1742 ,0.0789 , 0.1886 , 0.1042 , 0.1186 , 0.1665 , 0.0761 , 0.0917 , 0.0743 , 0.1918 , 0.1251 , 0.1358 , 0.0550 , 0.0491 , 0.1206 , 0.1096 , 0.0999 , 0.0508, 0.1260 , 0.1547 , 0.0412 , 0.1680 , 0.1015 , 0.0659 , 0.0842 , 0.0520 , 0.0965 , 0.1365 , 0.0520 , 0.0863 , 0.1296 , 0.1176]
#
# epochs = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40]
# #print(len(epochs) , len(reg_loss) , len(val_regressL))
#
# plt.plot(epochs,reg_loss , epochs, val_regressL)
# plt.xlabel("Epochs")
# plt.ylabel("Losses")
# plt.title("Regression Loss")
# plt.legend(['Regression Loss ', 'Validation Regression Loss'])
# plt.show()