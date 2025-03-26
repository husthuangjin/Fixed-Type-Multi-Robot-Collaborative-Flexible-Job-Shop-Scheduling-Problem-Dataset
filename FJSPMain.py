import os
import numpy as np
import xlwt
import time
from FJSPMIPModel import MIPModel

files = os.listdir('./hdata') 
# files = ["hj01.fjs"]
file_path = "./gantt_result/hdata/"
largeM = 0
save_data = np.zeros((len(files), 4))
number = 0

for file in files:
    inputfile = os.path.join('./hdata/'+file)
    # inputfile = os.path.join('./hdata/'+'hj34.fjs')
    # 首先读取标准数据集数据
    with open(inputfile, 'r') as stream1:
        data_firstline = stream1.readline().split()
        job_count, machine_count, muti_machine_count = int(data_firstline[0]), int(data_firstline[1]), int(data_firstline[2])
        procedure_count = []
        M_table = []
        T_table = []
        V_table = []

        for i in range(job_count):
            data_line = stream1.readline().split()
            procedure_count.append(int(data_line[0]))

            T_row = []
            M_row = []
            V_row = []
            m = 1

            for j in range(procedure_count[i]):
                machine_list = [0]*(machine_count - muti_machine_count + 1)
                time_list = [0]*(machine_count - muti_machine_count + 1)
                v_list = [0]*(muti_machine_count)

                temp = int(data_line[m])

                m = m + 1
                protimemax = 0
                if temp > 0:
                    for k in range(temp):
                        machine, mac_time = map(int, data_line[m:m + 2])
                        machine_list[machine - 1] = 1
                        v_list[0] = 1
                        time_list[machine - 1] = mac_time
                        m = m + 2
                        if protimemax < mac_time:
                            protimemax = mac_time
                else:
                    machine, mac_time = map(int, data_line[m:m + 2])
                    machine_list[machine - 1] = 1
                    v_list = [1]*(muti_machine_count)
                    # v_list[0] = 0
                    time_list[machine - 1] = mac_time
                    m = m + 2*abs(temp)
                    if protimemax < mac_time:
                        protimemax = mac_time                    
                largeM = largeM + protimemax

                M_row.append(machine_list)
                T_row.append(time_list)
                V_row.append(v_list)

            M_table.append(M_row)
            T_table.append(T_row)
            V_table.append(V_row)

    JobNum = job_count
    MacNum = machine_count - muti_machine_count + 1
    OpNum = procedure_count
    M_table = np.array(M_table)
    T_table = np.array(T_table)
    V_table = np.array(V_table)
    
    x, y, b = {}, {}, {}
    mipmodel=MIPModel(job_count, MacNum, OpNum, M_table, T_table, V_table, largeM, x, y, b, muti_machine_count)
    # mipmodel.write("model.lp")
    mipmodel.optimize()
    save_data[number,0] = round(mipmodel.ObjVal)
    save_data[number,1] = round(mipmodel.ObjBound)
    save_data[number,2] = round(mipmodel.Runtime, 2)
    save_data[number,3] = round(mipmodel.getAttr("MIPGap"), 2)
    number += 1
    
    machine_table = [[] for _ in range(MacNum)]  #机器表，用于后续绘制甘特图
    for i in range(len(mipmodel.getAttr("x",x).keys())):
        if x[mipmodel.getAttr("x",x).keys()[i]].x > 0: #判断他的值是否大于0
            j = mipmodel.getAttr("x",x).keys()[i][0]
            o = mipmodel.getAttr("x",x).keys()[i][1]
            ma = mipmodel.getAttr("x",x).keys()[i][2]
            machine_table[ma].append((j, o, int(b[j, o, ma].x), int(b[j, o, ma].x + T_table[j][o][ma] 
                                                                            /(mipmodel.getAttr("x",x).keys()[i][3]+1)))) #除以加工模式
    
    save_gantt_data = f"{JobNum} {machine_count} {round(mipmodel.ObjVal) } {muti_machine_count}\n" #接下来按照李老师的甘特图绘制上位机准备数据格式
    for i in range(MacNum):
        machine_table[i] = sorted(machine_table[i], key=lambda x: x[2])
        
        save_gantt_data += f"{len(machine_table[i])} "
        for j in range(len(machine_table[i])):
             save_gantt_data += f"{machine_table[i][j][0]} {machine_table[i][j][1]} " 
        for j in range(len(machine_table[i])):
             save_gantt_data += f"{machine_table[i][j][2]} {machine_table[i][j][3]} "  
        save_gantt_data += "\n"

    with open(os.path.join(file_path+file[:-4]+".txt"), 'w') as file_writer:
        file_writer.write(save_gantt_data)

    print("success obtain:" + str(file))
    # print("Calculation time: "+ str(mipmodel.Runtime))
    # print("result: "+ str(mipmodel.ObjVal))
    # print("lower bound: "+ str(mipmodel.ObjBound))

wb = xlwt.Workbook()
sheet = wb.add_sheet('sheet1')
for i in range(len(save_data)):
    sheet.write(i, 0, files[i][:-4])
    sheet.write(i, 1, str(save_data[i][0]))
    sheet.write(i, 2, str(save_data[i][1]))
    sheet.write(i, 3, str(save_data[i][2]))
    sheet.write(i, 4, str(save_data[i][3]))
t = time.localtime()
wb.save('./save_data/edata'+str(t.tm_year)+str(t.tm_mon)+str(t.tm_mday)+str(t.tm_hour)+str(t.tm_min)+'.xls')