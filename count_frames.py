import cv2
p='source\\start_np_11.mp4'
cap=cv2.VideoCapture(p)
if not cap.isOpened():
    print('cannot open', p)
else:
    total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps=cap.get(cv2.CAP_PROP_FPS) or 0
    print('reported frames', total, 'fps', fps)
    i=0
    while True:
        ret,frame=cap.read()
        if not ret: break
        i+=1
        if i%100==0:
            print('read',i)
    print('read total',i)
    cap.release()
