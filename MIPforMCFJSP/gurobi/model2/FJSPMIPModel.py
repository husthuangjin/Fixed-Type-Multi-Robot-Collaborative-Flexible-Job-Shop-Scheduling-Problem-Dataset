from gurobipy import Model, GRB, quicksum
import sys

def MIPModel(job_count, MacNum, OpNum, M_table, T_table, V_table, largeM, x, y, b, mutiNum):

    model = Model("FJSP_PPF")
    cmax = model.addVar(lb=0, ub=largeM, vtype="I", name="cmax")
    E = model.addVar(lb=0, ub=largeM, vtype="I", name="cmax")
    for i in range(job_count):  # job
        for j in range(OpNum[i]):  # operation
            # s[j,i]=model.addVar(lb=0,ub=largeM,vtype="I",name="s(%s,%s)"%(j,i))
            b[i, j] = model.addVar(lb=0, ub=largeM, vtype="I", name="b(%s,%s)" % (i, j))  # ltimeOp[j,i]
            for k in range(MacNum):
                if M_table[i][j][k] > 0:
                    for v in range(mutiNum):
                        if V_table[i][j][v] > 0:
                            x[i, j, k, v] = model.addVar(lb=0, ub=1, vtype="B", name="x(%s,%s,%s,%s)" % (i, j, k, v))
    # define y
    for i in range(job_count):
        for ip in range(job_count):
            for j in range(OpNum[i]):
                for jp in range(OpNum[ip]):
                    y[i, j, ip, jp] = model.addVar(lb=0, ub=1, vtype="B", name="y(%s,%s,%s,%s)" % (i, j, ip, jp))

    # define objective function
    model.setObjective(0.9*cmax+0.1*E, GRB.MINIMIZE) #求取最小值
    # constraint(3)
    for i in range(job_count):
        for j in range(OpNum[i]):
            model.addConstr(quicksum(quicksum((x[i, j, k, v]) for v in range(mutiNum) if V_table[i][j][v] > 0) for k in range(MacNum) if M_table[i][j][k] > 0) == 1, "assignment(%s,%s)" % (i, j))
                    
    # constraint(4)
    for i in range(job_count):
        for j in range(OpNum[i]-1):
                model.addConstr(b[i, j] + quicksum(quicksum((T_table[i, j, k] * x[i, j, k, v]/(v + 1)) for v in range(mutiNum) if V_table[i][j][v] > 0) 
                                                   for k in range(MacNum) if M_table[i][j][k] > 0) <= b[i, j+1], "stime(%s,%s)" % (i, j)) #存储operations_machines里面工件工序存储机器
    # constraint(5)
    for i in range(job_count):
        for ip in range(job_count):
            if i < ip:
                for j in range(OpNum[i]):
                    for jp in range(OpNum[ip]):
                        for k in range(MacNum):
                            if M_table[i][j][k] > 0 and M_table[ip][jp][k] > 0:
                                model.addConstr(b[i, j] + quicksum((T_table[i, j, k]*x[i, j, k, v]/(v + 1)) for v in range(mutiNum) if V_table[i][j][v] > 0) <=  b[ip, jp] + 
                                                largeM*(3 - y[i, j, ip, jp] - (quicksum((x[i, j, k, v]) for v in range(mutiNum) if V_table[i][j][v] > 0)) - 
                                                        (quicksum((x[ip, jp, k, vp]) for vp in range(mutiNum) if V_table[ip][jp][vp] > 0))),
                                                        "cons_6_(%s,%s,%s,%s)" % (i, j, ip, jp))
                                
                                model.addConstr(b[ip, jp] + quicksum((T_table[ip, jp, k]*x[ip, jp, k, vp]/(vp + 1)) for vp in range(mutiNum) if V_table[i][j][vp] > 0) <= b[i, j] + 
                                                largeM * (2 + y[i, j, ip, jp] - (quicksum((x[i, j, k, v]) for v in range(mutiNum) if V_table[i][j][v] > 0))
                                                          - (quicksum((x[ip, jp, k, vp]) for vp in range(mutiNum) if V_table[ip][jp][vp] > 0))),
                                                          "cons_5_(%s,%s,%s,%s)" % (i, j, ip, jp))
    # cmax constraint
    for i in range(job_count):
        model.addConstr(cmax >= b[i, OpNum[i]-1] + quicksum(quicksum((T_table[i, OpNum[i]-1, k] * x[i, OpNum[i]-1, k, v]/(v + 1)) 
                                                             for v in range(mutiNum) if V_table[i][j][v] > 0) for k in range(MacNum) if M_table[i][OpNum[i]-1][k] > 0),
                                                              "cmax_cons_(%s)" % (i))
    sum_E = 0
    for i in range(job_count):  # job
        for j in range(OpNum[i]):  # operation
            for k in range(MacNum):
                if M_table[i][j][k] > 0:    
                    sum_E += quicksum((x[i, j, k, v]*(v + 1)) for v in range(mutiNum) if V_table[i][j][v] > 0)
    model.addConstr(E >= sum_E)

    model.params.TimeLimit = 600
    model.setParam('Threads',30)
    # model.setParam('MIPGap', 0.1)
    model.update()
    return model