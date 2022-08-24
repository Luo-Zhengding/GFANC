from os import write
import os
from sklearn.utils import shuffle
import torch 
from torch import nn
import torch.nn.functional as F
from torch.utils.data import DataLoader 
import torch.optim as optim
from sklearn.metrics import classification_report
import numpy as np

from MyDataLoader import MyNoiseDataset
from Bcolors import bcolors
from M5_Network import m3, m5, m11, m18, m34_res, m6_res

BATCH_SIZE = 250
EPOCHS = 50

# using uniform distribution for weight initialization
def init_weights(m):
    if isinstance(m, torch.nn.Conv1d):
        torch.nn.init.xavier_uniform_(m.weight.data)

def create_data_loader(train_data, batch_size):
    train_dataloader = DataLoader(train_data, batch_size)
    return train_dataloader

def train_single_epoch(model, data_loader, loss_fn, optimizer, device):
    train_loss = 0
    train_acc = 0
    model.train()
    
    for input, target in data_loader:
        input, target = input.to(device), target.to(device)
        
        # calculate loss
        prediction = model(input)
        loss = loss_fn(prediction,target) # prediction & target: float

        # backpropagate 
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # Recording the loss and accuracy
        train_loss += loss.item()
        num_correct = sum(row.all().int().item() for row in (prediction.ge(0.5) == target)) # !!! Threshold
        acc = num_correct / input.shape[0]
        train_acc += acc

    print(f"Training Loss: {train_loss/len(data_loader)}" + f" Training Accuracy: {train_acc / len(data_loader)}") 
    return train_acc/len(data_loader), train_loss/len(data_loader)

def validate_single_epoch(model, eva_data_loader, loss_fn, device):
    eval_loss = 0
    eval_acc = 0
    model.eval()

    for input, target in eva_data_loader:
        input, target = input.to(device), target.to(device)
        
        # Calculating the loss value
        prediction = model(input)
        loss = loss_fn(prediction,target)

        # recording the validating loss and accuratcy
        eval_loss += loss.item()
        num_correct = sum(row.all().int().item() for row in (prediction.ge(0.5) == target)) # !!! Threshold
        acc = num_correct / input.shape[0]
        eval_acc += acc

    print(f"Validation Loss : {eval_loss/len(eva_data_loader)}" + f" Validation Accuracy : {eval_acc/len(eva_data_loader)}") 
    return eval_acc/len(eva_data_loader), eval_loss/len(eva_data_loader)

def train(model, data_loader, eva_data_loader, epochs, device, MODEL_PTH=None):
    acc_max = 0 
    acc_train_max = 0
    loss_fn = nn.BCELoss() # change to BCELoss
    optimizer = optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4) # L2 regularization
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)  # reduce the learning after 5 epochs
    train_loss_epochs = []
    validate_loss_epochs = []
    
    for i in range(epochs):
        print(f"Epoch {i+1}")
        print("Learning rate:", optimizer.param_groups[0]['lr'])
        acc_train, train_loss_epoch = train_single_epoch(model, data_loader, loss_fn, optimizer, device)
        acc_validate, validate_loss_epoch = validate_single_epoch(model, eva_data_loader, loss_fn, device)
        scheduler.step() # after every epoch update learning rate
        train_loss_epochs.append(train_loss_epoch)
        validate_loss_epochs.append(validate_loss_epoch)
        
        if acc_validate > acc_max:
            acc_train_max, acc_max = acc_train, acc_validate
            torch.save(model.state_dict(), MODEL_PTH)
            print(bcolors.OKCYAN+ "Trained feed forward net saved at " + MODEL_PTH + bcolors.ENDC)   
        print("----------------------------------")
    print("Finished trainning")
    return acc_train_max, acc_max, train_loss_epochs, validate_loss_epochs


#----------------------------------------------------------------------------------------
# Function : Training and validating 1D-CNN
#----------------------------------------------------------------------------------------
def Train_Validate_CNN(TRIAN_DATASET_FILE, VALIDATION_DATASET_FILE, MODEL_PTH, File_sheet):
    
    train_data = MyNoiseDataset(TRIAN_DATASET_FILE,File_sheet)
    valid_data = MyNoiseDataset(VALIDATION_DATASET_FILE,File_sheet)
    
    train_dataloader = create_data_loader(train_data, BATCH_SIZE)
    valid_dataloader = create_data_loader(valid_data, BATCH_SIZE)
    
    # set the model
    model = m6_res
    model.apply(init_weights)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') # begin from #0 gpu
    model = model.to(device)

    # train model
    acc_train, acc_validate, train_loss_epochs, validate_loss_epochs = train(model, train_dataloader, valid_dataloader, EPOCHS, device, MODEL_PTH)

    return acc_train, acc_validate, train_loss_epochs, validate_loss_epochs