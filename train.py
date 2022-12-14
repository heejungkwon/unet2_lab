# -*- coding: utf-8 -*-
"""
defacto dataset으로 RRU-Net 네트워크 훈련 코드
python train.py로 네트워크 훈련한 다음 RRU_train_test.ipynb 파일에서 결과 확인
가까운 시일 내 predict.py로 성능평가 해야 함 
"""

import torch.backends.cudnn as cudnn
import torch
from torch import nn
from torch import optim
from model.unet_model import Ringed_Res_Unet
from model.UNet_2Plus import UNet_2Plus
from dataset.Defacto import load_dataset
import matplotlib.pyplot as plt
import time,os
# __________________________________________
from loss.dice_loss import dice_coeff

def train_net(net,
              epochs=5,
              batch_size=1,
              img_size=512,
              lr=1e-2,
              save_cp=True,
              gpu=True,
              dataset=None,
              dir_logs=None):
    # training images are square
    # ids = split_ids(get_ids(dir_img))
    # iddataset = split_train_val(ids, val_percent)

    # splicing_1_img 개수는 12187
    train_dataloader, val_dataloader = load_dataset(500,
                                                    img_size,
                                                    batch_size,
                                                    dir_img =  r'D:\dataset\splicing_1_img-20221031T095725Z-001\splicing_1_img\img',
                                                    dir_mask =  r"D:\dataset\splicing_1_annotations-20221031T104824Z-001\splicing_1_annotations\probe_mask"
    )


    print(f'''
    Starting training:
        Epochs: {epochs}
        Batch size: {batch_size}
        Image size: {img_size}
        Learning rate: {lr}
        Training size: {train_dataloader.__len__()}
        Validation size: {val_dataloader.__len__()}
        Checkpoints: {str(save_cp)}
        CUDA: {str(gpu)}
    ''')
    # return 0
    N_train = train_dataloader.__len__()

    optimizer = optim.Adam(net.parameters(),
                           lr=lr)
    criterion = nn.BCELoss()

    Train_loss  = []
    Valida_dice = []
    EPOCH = []
    spend_total_time = []
    

    for epoch in range(epochs):
        net.train()

        start_epoch = time.time()
        print('Starting epoch {}/{}.'.format(epoch + 1, epochs))
        epoch_loss = 0.0

        for i, data in enumerate(train_dataloader):
            start_batch = time.time()
            imgs = data['image']
            true_masks = data['landmarks']
    
            if gpu:
                imgs = imgs.cuda()
                true_masks = true_masks.cuda()

            optimizer.zero_grad()

            masks_pred = net(imgs)
            masks_probs = torch.sigmoid(masks_pred)
            masks_probs_flat = masks_probs.view(-1)
            true_masks_flat = true_masks.view(-1)
            loss = criterion(masks_probs_flat, true_masks_flat)

            print('{:.4f} --- loss: {:.4f}, {:.3f}s'.format(i * batch_size / N_train, loss, time.time()-start_batch))

            epoch_loss += loss.item()

            loss.backward()
            optimizer.step()

        print('Epoch finished ! Loss: {:.4f}'.format(epoch_loss / i))

        # validate the performance of the model
        with torch.no_grad():
            net.eval()
            tot = 0

            for i,val in enumerate(val_dataloader):
                img = val['image']
                true_mask = val['landmarks']
               
                if gpu:
                    img = img.cuda()
                    true_mask = true_mask.cuda()
               
                mask_pred = net(img)[0]
                mask_pred = (torch.sigmoid(mask_pred) > 0.5).float()

                tot += dice_coeff(mask_pred, true_mask).item()

            val_dice = tot / i
        print('Validation Dice Coeff: {:.4f}'.format(val_dice))

        Train_loss.append(epoch_loss / i)
        Valida_dice.append(val_dice)
        EPOCH.append(epoch)
            
        fig = plt.figure()
        plt.title('Training Process')
        plt.xlabel('epoch')
        plt.ylabel('value')
        l1, = plt.plot(EPOCH, Train_loss, c='red')
        l2, = plt.plot(EPOCH, Valida_dice, c='blue')

        plt.legend(handles=[l1, l2], labels=['Tra_loss', 'Val_dice'], loc='best')
        plt.savefig(dir_logs + 'Training Process for lr-{}.png'.format(lr), dpi=600)
        plt.close()
        if epoch %4== 0:
            torch.save(net.state_dict(),
                   dir_logs + '{}-[val_dice]-{:.4f}-[train_loss]-{:.4f}.pkl'.format(dataset, val_dice, epoch_loss / i))
        spend_per_time = time.time() - start_epoch
        print('Spend time: {:.3f}s'.format(spend_per_time))
        spend_total_time.append(spend_per_time)
        print()

    Tt = int(sum(spend_total_time))    
    print('Total time : {}m {}s'.format(Tt//60,Tt%60))

def main():
    # config parameters
    epochs = 50
    batchsize = 1
    image_size = 256 #  x(512,512,3) y(512,512,1)
    gpu = True
    lr = 1e-3
    checkpoint = False
    dataset = "defactor" #'CASIA'
    model = 'Ringed_Res_Unet'
    dir_logs = './result/logs/{}/{}/'.format(dataset, model)

    # log directory 생성
    os.makedirs(dir_logs,exist_ok=True)

    net = UNet_2Plus(in_channels=3, n_classes=1)

    # 훈련 epoch 나눠서 진행 할 때 True 사용
    if checkpoint:
        net.load_state_dict(torch.load('./result/logs/{}/{}/defactor-[val_dice]-0.2679-[train_loss]-2.4120.pkl'.format(dataset, model)))
        print('Load checkpoint')

    if gpu:
        net.cuda()
        cudnn.benchmark = True  # faster convolutions, but more memory

    train_net(net=net,
              epochs=epochs,
              batch_size=batchsize,
              img_size=image_size,
              lr=lr,
              gpu=gpu,
              dataset=dataset,
              dir_logs=dir_logs)

if __name__ == '__main__':
    main()
