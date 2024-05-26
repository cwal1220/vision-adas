import cv2

# 웹캠 열기
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

if not cap.isOpened():
    print("웹캠을 열 수 없습니다.")
    exit()

# 프레임의 너비와 높이 얻기
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))

# VideoWriter 객체 생성
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 'mp4v' 코덱 사용
out = cv2.VideoWriter('output.mp4', fourcc, 20.0, (frame_width, frame_height))

while True:
    # 프레임 읽기
    ret, frame = cap.read()
    
    if not ret:
        print("프레임을 가져올 수 없습니다.")
        break
    
    # 프레임을 파일에 쓰기
    out.write(frame)
    
    # 프레임을 윈도우에 표시
    cv2.imshow('Webcam Feed', frame)
    
    # 'q' 키를 누르면 루프 탈출
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 웹캠과 VideoWriter 객체 해제, 윈도우 닫기
cap.release()
out.release()
cv2.destroyAllWindows()
