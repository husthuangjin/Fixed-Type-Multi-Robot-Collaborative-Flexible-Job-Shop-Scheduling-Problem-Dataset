from docplex.cp.model import *
import os
import docplex.cp.utils_visu as visu
import random
import numpy as np
import xlwt
import time
#-----------------------------------------------------------------------------
# Initialize the problem data
#-----------------------------------------------------------------------------

files = os.listdir('./hdata/')
file_path = "./gantt_result/"
file_path1 = "./log_result/"
save_data = np.zeros((len(files), 4))
number = 0

for fi in files:
    filename = os.path.join('./hdata/'+fi)
    with open(filename, 'r') as file:
        NB_JOBS, NB_MACHINES, NB_MUTI = [int(v) for v in file.readline().split()]
        list_jobs = [[int(v) for v in file.readline().split()] for i in range(NB_JOBS)]


    #-----------------------------------------------------------------------------
    # Prepare the data for modeling
    #-----------------------------------------------------------------------------

    # Build final list of jobs.
    # Each job is a list of operations.
    # Each operation is a list of choices expressed as tuples (machine, duration)
    JOBS = []
    muti_operation_jobs = []
    muti_operations_num = []
    # muti_machine_num = 4 #多机协同机器数量，如果后续要做对比实验需要将此处数值改为1
    oper_time = []
    for jline in list_jobs:
        nbstps = jline.pop(0)
        job = []
        muti_job = []
        muti_num = []
        operation_num = 0
        for stp in range(nbstps):
            nbc = jline.pop(0)
            choices = []
            muti_choices = []
            if nbc < 0:
                for c in range(abs(nbc)):
                    m = jline.pop(0)
                    d = jline.pop(0)
                    muti_choices.append((m - 1, d))
                muti_job.append(muti_choices)  #存储每个工件需要多机协同加工工序
                muti_num.append(operation_num) #存储每个工件需要多机协同加工工序编号
                job.append(muti_choices)
            else:
                for c in range(nbc):
                    m = jline.pop(0)
                    d = jline.pop(0)
                    choices.append((m - 1, d))
                job.append(choices)  #存储所有加工对应可选加工机器和加工时间
            oper_time.append(d)
            operation_num = operation_num + 1
        JOBS.append(job)
        muti_operation_jobs.append(muti_job)
        muti_operations_num.append(muti_num)

    #-----------------------------------------------------------------------------
    # Build the model
    #-----------------------------------------------------------------------------

    # Create model
    mdl = CpoModel()
    job_number = {}  # 每个建个变量表示的是第几个工件
    all_operations = []  # 存储所有工序的列表
    machine_operations = [[] for m in range(NB_MACHINES-NB_MUTI+1)]  # 每台机器上可加工的工序
    # Loop on all jobs/operations/choices 循环JOBS列表
    muti_operation_name = []

    for jx, job in enumerate(JOBS):  # 第jx个工件
        op_vars = []
        muti_jobs = muti_operation_jobs[0]
        muti_operation_jobs = muti_operation_jobs[1:] #切片，每次工件更新后，多机协同加工工件也要进行更新

        for ox, op in enumerate(job):  # 第ox道工序
            if ox in muti_operations_num[jx]: #判断该工序是否属于多机加工工序之中，如果是由于静态加工，必须要等该工序加工完成
                op = muti_jobs[0]
                muti_jobs = muti_jobs[1:]
                choice_vars = []
                for i in range(len(op)):  # 第cx个可选的机器 ，机器m , 加工时间为d
                    d = op[0][1]  # 由于所有机器加工时间一致
                    # jx代表是工件编号，ox代表为工序编号，i代表机器组合数，m_flag是巧用二进制数表示所选择机器组合
                    cv = mdl.interval_var(name="J{}_O{}_C{}_M{}".format(jx, ox, i, i), optional=True, size=d // (i+1))
                    job_number[cv.get_name()] = jx, ox  # k:J0_O0_C0_M1 v:0
                    choice_vars.append(cv)  # 每道工序的可选间隔变量
                    muti_operation_name.append(cv.get_name())
                    machine_operations[op[0][0]].append(cv)  # 每台机器的可选间隔变量集合
                # 创建间隔变量A2，相当于为每个任务每道工序设置一个间隔变量，
                jv = mdl.interval_var(name="J{}_O{}".format(jx, ox))
                # 添加约束1：我们会发现A1和A2之间有一个约束，A2可从上次循环得到的所有间隔变量中仅且只能从中选择一个，约束如下
                mdl.add(mdl.alternative(jv, choice_vars))
                op_vars.append(jv)
                # 添加约束2：每道工序只有在前道工序加工完成后才能进行后道工序加工
                if ox > 0:  # 工序不是第一道工序
                    mdl.add(mdl.end_before_start(op_vars[ox - 1], op_vars[ox]))

            else:
                choice_vars = []
                for cx, (m, d) in enumerate(op):  # 第cx个可选的机器 ，机器m , 加工时间为d
                    # 创建间隔变量A1，例如J0_O0_C0_M1 就表示第一个工件的第一道工序的第一个可选的机器是M1
                    cv = mdl.interval_var(name="J{}_O{}_C{}_M{}".format(jx, ox, cx, m), optional=True, size=d)
                    job_number[cv.get_name()] = jx, ox  # k:J0_O0_C0_M1 v:0
                    choice_vars.append(cv)  # 每道工序的可选间隔变量
                    machine_operations[m].append(cv)  # 每台机器的可选间隔变量集合
                # 创建间隔变量A2，相当于为每个任务每道工序设置一个间隔变量，
                jv = mdl.interval_var(name="J{}_O{}".format(jx, ox))
                # 添加约束1：一个工件工序只能选择一种多机加工模式约束
                mdl.add(mdl.alternative(jv, choice_vars))
                op_vars.append(jv)
                # 添加约束2：每道工序只有在前道工序加工完成后才能进行后道工序加工
                if ox > 0:  # 工序不是第一道工序
                    mdl.add(mdl.end_before_start(op_vars[ox - 1], op_vars[ox]))

        all_operations.extend(op_vars)  # 保存所有工序的间隔变量

    # 添加约束3：每台机器上的工序是不能重复的部分
    for lops in machine_operations:
        if len(lops) > 0:
            mdl.add(mdl.no_overlap(lops))

    # 目标函数：所有工序的完工时间最小
    ob1 = max(end_of(op) for op in all_operations)
    # ob2 = sum((end_of(lops) - start_of(lops)) for lops in machine_operations)
    ob2 = sum(oper_time[o]/(end_of(ops) - start_of(ops)) for o, ops in enumerate(all_operations))
    mdl.add(mdl.minimize(ob1*0.9+ob2*0.1))

    # Solve model
    print('Solving model...')
    start_time = time.time()
    msol = mdl.solve(TimeLimit=600)
    end_time = time.time()
    print(end_time-start_time)
    with open(os.path.join(file_path1 + fi[:-4] + ".log"), 'w') as file_writer:
        file_writer.write(msol.solver_log)

    save_data[number, 0] = msol.solution.objective_values[0]
    save_data[number, 1] = end_time - start_time
    save_data[number, 2] = msol.solution.get_objective_bound()
    save_data[number, 3] = msol.solution.get_objective_gap()
    number = number + 1

    save_gantt_data = f"{NB_JOBS} {NB_MACHINES} {msol.solution.objective_values[0]} {NB_MUTI}\n"

    if msol and visu.is_visu_enabled():
        for j in range(NB_MACHINES-NB_MUTI+1):
            number_machine_process_job = 0  # 机器实际加工工件数
            for v in machine_operations[j]:  # 循环遍历所有机器上选择的间隔变量
                itv = msol.get_var_solution(v)  # 获得所有的间隔变量
                if itv.is_present():  # 如果间隔变量存在
                    number_machine_process_job += 1

            save_gantt_data += f"{number_machine_process_job} "
            for v in machine_operations[j]:  # 循环遍历所有机器上选择的间隔变量
                itv = msol.get_var_solution(v)  # 获得所有的间隔变量
                if itv.is_present():  # 如果间隔变量存在
                    save_gantt_data += f"{job_number[v.get_name()][0]} {job_number[v.get_name()][1]} "

            for v in machine_operations[j]:  # 循环遍历所有机器上选择的间隔变量
                itv = msol.get_var_solution(v)  # 获得所有的间隔变量
                if itv.is_present():  # 如果间隔变量存在
                    save_gantt_data += f"{itv.start} {itv.end} "

            save_gantt_data += "\n"

    with open(os.path.join(file_path + fi[:-4] + ".txt"), 'w') as file_writer:
        file_writer.write(save_gantt_data)

wb = xlwt.Workbook()
sheet = wb.add_sheet('sheet1')
for i in range(len(save_data)):
    sheet.write(i, 0, files[i][:-4])
    sheet.write(i, 1, str(save_data[i][0]))
    sheet.write(i, 2, str(save_data[i][1]))
    sheet.write(i, 3, str(save_data[i][2]))
    sheet.write(i, 4, str(save_data[i][3]))
t = time.localtime()
wb.save('save_hdata' + str(t.tm_year) + str(t.tm_mon) + str(t.tm_mday) + str(t.tm_hour) + str(t.tm_min) + '.xls')