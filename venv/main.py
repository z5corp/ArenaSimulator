
import configparser
import json
import math

#character stats
#starting position
#battle buffs

#캐릭터 전투 init 데이터
base_stats = []
stats = []
skillData = []
initPositions = []
mspd = 5 #coordinate per frame
#캐릭터 전투 연산 데이터
lastPosition = []
inmove = [[0],[0],[0],[0],[0],[0],[0],[0],[0],[0]]
nextSkill = [-1,-1,-1,-1,-1,-1,-1,-1,-1,-1]  #다음에 사용할 스킬
skillUsedTf = [] #마지막으로 스킬을 사용한 timeframe 기록
c_targetable = [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]] #캐릭터가 타겟팅 가능한 스테이트인지 보유
c_list = []
ctf_list = [9999,9999,9999,9999,9999,9999,9999,9999,9999,9999]
hp = []
battle_time = 60 * 180  # 전투 시간 1분30초 60프레임

############### 전투 데이터 upload ###############
def loadBattleData():

    global initPositions
    global skillUsedTf
    global base_stats
    global skillData

    with open("battledata") as json_data:
        bd = json.load(json_data)

    for c in bd['battledata']:
        base_stats.append(c['stats'])
        skillData.append([c['char_no'],0,c['skill0']])
        skillData.append([c['char_no'],1,c['skill1']])
        skillData.append([c['char_no'],2,c['skill2']])
        skillData.append([c['char_no'],3,c['skill3']])
        skillData.append([c['char_no'],4,c['skill4']])

    print('base_stats: ',base_stats)
    print('skillData: ',skillData)
    #전투 셋팅 데이터 불러오기
    config = configparser.ConfigParser()
    config.read('battle_setting')
    initPositions = json.loads(config.get('battleSettings','initPositions'))
    skillUsedTf = json.loads(config.get('battleSettings','skillUsedTf'))

############### init battle base data ###############
def init():
    global lastPosition
    global initPositions
    global c_list
    lastPosition.extend(initPositions)
    c_list = [i[0] for i in base_stats if i[0] != 0]
    for x in c_list:
        ctf_list[x-1] = 1
        c_targetable[x-1][0] = 1
    print('참여 캐릭터 리스트: ',c_list)
    print('액션 timeframe: ',ctf_list)

def getStat(char_no,statType,timeframe): #필요한 캐릭터의 스탯 가져오기
    statTypeList = ['char_no','side','position','lv','hp','atk','def','crit','acc','dodge','haste','recv','mresist','presist','leech']
    tmp_stat = [i[statTypeList.index(statType)] for i in base_stats if i[0] == char_no]
    return tmp_stat[0]

def getSkillData(char_no,skill_no,dataType):
    skillDataList = ['cooldown','range','targetMove','targetAction']
    for c in skillData:
        if c[0]==char_no:
            if c[1]==skill_no:
                tmp_skilldata = c[2][skillDataList.index(dataType)]
    return tmp_skilldata

def setMove(char_no,target_no,timeframe):  #캐릭터를 이동시키는 함수
    skill_no = nextSkill[char_no-1]
    startPosition = getPosition(char_no,timeframe)
    targetPosition = getPosition(target_no,timeframe)
    #checkInRange
    inRange = checkInRange(char_no,target_no,timeframe)
    if inRange==0: #타겟이 범위내에 없을 경우 이동한다.
        t_mdata = inmove[target_no-1][0]
        if t_mdata == 0:
            #endPosition구하기
            skillRange = stats[char_no - 1][20 + skill_no]
            endPosition = getEndPosition(startPosition,targetPosition,skillRange)
            #endTimeframe구하기
            y = endPosition[1] - startPosition[1]
            x = endPosition[0] - startPosition[0]
            range = round(math.sqrt(x ** 2 + y ** 2), 1)
            #range = y / math.sin(math.atan2(y,x))
            duration = round(range/getMspd(char_no,timeframe),0)
            endTimeframe = duration + timeframe
            #write data to inmove[]
            inmove[char_no-1] = [1, startPosition[0],startPosition[1],timeframe,endPosition[0],endPosition[1],endTimeframe]
            print('inmove: ',inmove[char_no-1])
            lastPosition[char_no-1]=endPosition
            ctf_list[char_no-1] = endTimeframe+1
        elif t_mdata == 1:
            moveFix(char_no,target_no,timeframe)

    else:
        #타겟이 사거리 이내에 있으므로 움직일 필요 없음.
        print("target in Range: no need to move")

def getMove(char_no,target_no,timeframe):
    inRange = checkInRange(char_no,target_no,timeframe)
    print('inRange: ',inRange)
    #사거리 이내
    if inRange==1:
        mdata=[0]
        setAction(char_no,timeframe)
    #사거리 밖
    elif inRange==0:
        t_mdata = inmove[target_no-1][0]
        if t_mdata==0:#타겟이 멈춰있을 경우
            tmp_mspd = mspd * (1+getStat(char_no,'haste',timeframe))
            range = getRange(char_no,target_no,timeframe)
            startPosition = getPosition(char_no,timeframe)
            endPosition = getEndPosition(char_no,target_no,timeframe)
            duration = range/tmp_mspd
            endTimeframe = timeframe+duration
            mdata=[1,startPosition[0],startPosition[1],timeframe,endPosition[0],endPosition[1],endTimeframe,target_no]
            inmove[char_no-1]=mdata
            lastPosition[char_no-1]=endPosition
            ctf_list[char_no-1]=endTimeframe+1
            print('move: ',inmove[char_no-1])
        elif t_mdata==1:#타겟이 이동중일 경우
            moveFix(char_no,target_no,timeframe)
            moveIterate(char_no,0,timeframe)

def moveIterate(char_no,pre_char_no,timeframe):
    for a, x in enumerate(inmove, 1):
        try:
            if x[7] == char_no and a!=pre_char_no :
                moveFix(a, char_no, timeframe)
                moveIterate(a,char_no,timeframe)
        except IndexError:
            continue

def getMspd(char_no,timeframe):
    tmp_mspd = mspd * (1+getStat(char_no,'haste',timeframe)) #todo: 버프 추가
    return tmp_mspd

def moveFix(char_no,target_no,timeframe):
    c2_mdata = inmove[target_no-1]  #mdata [이동중(0/1)/시작x/시작y/시작tf/도달x/도달y/도달tf]
    m2 = getMspd(char_no,timeframe)
    m1 = getMspd(target_no,timeframe)
    skill_no = nextSkill[char_no-1]
    r = getSkillData(char_no,skill_no,'range')
    c1_pos = getPosition(char_no,timeframe)
    px = c2_mdata[1] - c1_pos[0]  # target_x_start - mover_x
    py = c2_mdata[2] - c1_pos[1]  # target_y_start - mover_y
    d = math.sqrt((c2_mdata[4]-c2_mdata[1])**2+(c2_mdata[5]-c2_mdata[2])**2) #target move distance
    vx = (m2/d)*(c2_mdata[4]-c2_mdata[1])
    vy = (m2/d)*(c2_mdata[5]-c2_mdata[2])
    c = round(px**2 + py**2 - r**2,2)
    b = round(2*px*vx + 2*py*vy - 2*m1*r,2)
    a = round(vx**2 + vy**2 - m1**2,2)
    if a == 0:
        t = -c/b
    elif a>0:
        t1 = (-b+math.sqrt(b**2-4*a*c))/(2*a)
        print('t1',t1)
        t2 = (-b-math.sqrt(b**2-4*a*c))/(2*a)
        print('t2',t2)
        if t1 > 0 and t2 > 0:
            if t1 < t2:
                t = t1
            else:
                t = t2
        else:
            print('no interception point')
    if t > (c2_mdata[6]-timeframe):
        targetPosition = [c2_mdata[4],c2_mdata[5]]
    else:
        targetPosition = [c2_mdata[1]+vx*t,c2_mdata[2]+vy*t]
    endPosition = getEndPosition(char_no,targetPosition,timeframe)
    startPosition = c1_pos
    duration = getPosRange(endPosition,startPosition)/m2
    endTimeframe = timeframe + duration
    inmove[char_no - 1] = [1, startPosition[0], startPosition[1], timeframe, endPosition[0], endPosition[1], endTimeframe,target_no]
    print('char_no: ',char_no,'moveFixed: ', inmove[char_no - 1])
    ctf_list[char_no - 1] = endTimeframe+1
    lastPosition[char_no - 1] = endPosition
    #move랑 moveFix 정리

def getPosRange(positionA,positionB):
    x = positionB[0] - positionA[0]
    y = positionB[1] - positionA[1]
    range = round(math.sqrt(x**2 + y**2),1)
    return range

def getEndPosition(char_no,target,timeframe):
    skill_no = nextSkill[char_no-1]
    skillRange = getSkillData(char_no,skill_no,'range')
    startPosition = getPosition(char_no, timeframe)
    if type(target) is list:
        targetPosition = target
    else:
        targetPosition = getPosition(target, timeframe)
    y = targetPosition[1] - startPosition[1]
    x = targetPosition[0] - startPosition[0]
    a = math.sin(math.atan2(y,x))
    b = math.cos(math.atan2(y,x))
    endPosition_x = round(x - skillRange * b + startPosition[0],1)
    endPosition_y = round(y - skillRange * a + startPosition[1],1)
    endPosition = [endPosition_x, endPosition_y]
    return endPosition

def getRange(char_no,target_no,timeframe):
    positionA = getPosition(char_no,timeframe)
    positionB = getPosition(target_no,timeframe)
#    print('char_no',char_no,target_no,'포지션: ',positionA,positionB)

    #equation: 두개의 포지션으로 거리를 구하는 공식
    range = getPosRange(positionA,positionB)
    return range

def checkInRange(char_no,target_no,timeframe):
    skill_no = nextSkill[char_no-1]
    range = getRange(char_no,target_no,timeframe)
    atkRange = getSkillData(char_no,skill_no,'range')
    if range<=atkRange:
        inRange = 1
    else:
        inRange = 0
    return inRange

def getPosition(char_no,timeframe): #캐릭터의 특정 timeframe에서 포지션을 찾는 함수
    mdata = inmove[char_no-1]  #mdata [이동중(0/1)/시작x/시작y/시작tf/도달x/도달y/도달tf]

    if mdata[0]==0: #이동 중이 아닐 경우 마지막 등록 포지션 값 리턴
        tmp_position = lastPosition[char_no-1]
    elif mdata[0]==1: #이동 중일 경우 이동 벡트를 이용해 현재 포지션 구하기
        # variables
        tmp_mspd = getMspd(char_no,timeframe)

        # equation: 이동 벡터를 이용해 현재 포지션을 구하는 공식
        c = tmp_mspd * (timeframe - mdata[3])
        y = mdata[5]-mdata[2]
        x = mdata[4]-mdata[1]
        position_x = round(c * math.cos(math.atan2(y,x)) + mdata[1],1)
        position_y = round(c * math.sin(math.atan2(y,x)) + mdata[2],1)
        tmp_position = [position_x,position_y]
    else:
        print("Err: no move state. Char_no:"+char_no)
    return tmp_position

def setTarget(char_no,type,timeframe): #캐릭터가 타겟 지정
    skill_no = nextSkill[char_no-1]
    charSide = getStat(char_no,'side',timeframe)
    #targetType = ['range','near','','enemy',1] #change to get from database
    targetType = getSkillData(char_no,skill_no,type)[type]
    targetTeam = ''
    ranges = []
    tmp_targetList = []
    targetList = []

    #ally/enemy/all
    if  targetType[3] == 'ally':
        if charSide == 'L':
            targetTeam = 'L'
        else:
            targetTeam = 'R'
    elif targetType[3] == 'enemy':
        if charSide == 'L':
            targetTeam = 'R'
        else:
            targetTeam = 'L'
    elif targetType[3] == 'all':
        targetTeam = 'all'
    #char status targetable
    tmp_targetList.extend(checkTargetable(timeframe))
    try:
        tmp_targetList.remove(char_no)
    except:
        pass
    #targetTeam
    if targetTeam == 'L':
        tmp_targetList = [x for x in tmp_targetList if x<6]
    elif targetTeam == 'R':
        tmp_targetList = [x for x in tmp_targetList if x>5]

    #range
    if targetType[0] == 'range':
        for i in tmp_targetList:
            ranges.append([i,getRange(char_no,i,timeframe)])

    #range - near
    for i in range(0,targetType[4]):
        try:
            if targetType[1] == 'near':
                targetList.append(sorted(ranges,key=lambda target: target[1])[i][0])
            if targetType[1] == 'far':
                targetList.append(sorted(ranges,reverse= True,key=lambda target: target[1])[i][0])
        except IndexError:
            print("오류: 타겟 가능한 수 이상으로 타겟 검색")
    print('targeting:',targetList)
    return targetList

def checkTargetable(timeframe): #타겟 가능한 모든 캐릭터 목록 뽑기
    #타겟 가능 status인지 확인
    try:
        targetList = [i+1 for i, e in enumerate(c_targetable) if e[0]==1]
        #화면 밖 포지션인 캐릭터 제외
        outerbound = [400,400]

    except:
        print('no targetables')
        targetList = []

    return targetList

def setSkill(char_no,timeframe): #캐릭터가 다음 사용할 스킬을 선정
    #check Cooldown
    global skillUsedTf
    global nextSkill
    skillAvail = []

    for i in range(0,5):
        tmp_cooldown = timeframe - skillUsedTf[char_no-1][i] - getSkillData(char_no,i,'cooldown')
        if tmp_cooldown > 0 or skillUsedTf[char_no-1][i]==-1:
            skillAvail.append(i)

    #check Exception

    #check Priority: 스킬 넘버가 낮을수록 우선 순위 높음
    #select Skill
    tmp_nextSkill = skillAvail[0]
    #write Data
    nextSkill[char_no-1] = tmp_nextSkill
    print('char_no:',char_no,' skill_no:',tmp_nextSkill)

def setAction(char_no,timeframe):
    global skillUsedTf
#    skillUsedTf[char_no-1][tmp_nextSkill] = timeframe
    ctf_list[char_no-1]=timeframe+200
    print("액션액션!")

def setStatus(char_no,timeframe):
    print("작업예정")

def get_indexes_min_value(l): #c_list를 뽑을때 tf가 min인 char_no 뽑기
    min_value = min(l)
    if l.count(min_value) > 1:
        return [i+1 for i, x in enumerate(l) if x == min(l)]
    else:
        return [l.index(min(l))+1]

def resetExpired(timeframe):
    for i,e in enumerate(inmove):
        try:
            if e[6]<timeframe:
                inmove[i]=[0]
        except:
            continue



loadBattleData()
init()

n = 0
while n<10:
    n +=1
    #find char_no list with lowest tf
    c_list = get_indexes_min_value(ctf_list)
    print(c_list)
    resetExpired(min(ctf_list))
    for c in c_list:
        char_no = c
        print('-----------------------------------------')
        print('frame: ',ctf_list[char_no-1])
        print('-----------------------------------------')
        setSkill(char_no,ctf_list[char_no-1])
        target = setTarget(char_no,'targetMove',ctf_list[char_no-1])
        try:
            getMove(char_no,target[0],ctf_list[char_no-1])
        except:
            continue
