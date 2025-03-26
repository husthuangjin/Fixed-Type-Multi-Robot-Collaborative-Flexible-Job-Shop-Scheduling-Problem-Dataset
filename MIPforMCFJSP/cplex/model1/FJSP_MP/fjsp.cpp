#include <ilcplex/ilocplex.h>
#include <stdio.h>
#include<string> 
#include <fstream>
#include <iostream>
#include<vector>
#include <io.h>
#include <tuple>
#include <chrono>
#include <ctime>
using namespace std;

ILOSTLBEGIN
typedef IloArray<IloNumVarArray> IntVarMatrix;   //整数决策变量二维矩阵
typedef IloArray<IntVarMatrix>   IntVarMatrix3d; //整数决策变量三维矩阵
typedef IloArray<IntVarMatrix3d>   IntVarMatrix4d; //整数决策变量四维矩阵

int M = 0;

void getFiles(string path, vector<string>& files)
{
    //文件句柄
    intptr_t hFile = 0;
    //文件信息
    struct _finddata_t fileinfo;
    string p;
    if ((hFile = _findfirst(p.assign(path).append("\\*").c_str(), &fileinfo)) != -1)
    {
        do
        {
            //如果是目录,迭代之
            //如果不是,加入列表
            if ((fileinfo.attrib & _A_SUBDIR))
            {
                if (strcmp(fileinfo.name, ".") != 0 && strcmp(fileinfo.name, "..") != 0)
                    getFiles(fileinfo.name, files);
            }
            else
            {
                files.push_back(fileinfo.name);
            }
        } while (_findnext(hFile, &fileinfo) == 0);
        _findclose(hFile);
    }
}

int
main(void*) {
    string filePath = "./data/hdata/";
    string savepath = "./gantte_result/hdata/";
    vector<string> files;
    vector<std::tuple<string, int, double, int, double>> save_data;
    //获取该路径下的所有文件
    getFiles(filePath, files);
    //files = { "hj01.fjs"};

    for (const string& file : files)
    {
        IloEnv env;
        IloModel model(env);
        IloNumVarArray vars(env);
        string inputfile = filePath + file;
        ifstream stream1(inputfile);
        int job_count, machine_count, muti_machine_num;
        float candidate;
        stream1 >> job_count >> machine_count;
        stream1 >> muti_machine_num;
        machine_count = machine_count - muti_machine_num + 1;

        vector<int> procedure_count(job_count);
        vector<vector<vector<int>>> M_table;
        vector<vector<vector<int>>> T_table;
        vector<vector<vector<int>>> V_table;

        for (int i = 0; i < job_count; ++i) {
            stream1 >> procedure_count[i];

            vector<std::vector<int>> M_row;
            vector<std::vector<int>> T_row;
            vector<std::vector<int>> V_row;

            for (int j = 0; j < procedure_count[i]; ++j) {
                int temp;
                stream1 >> temp;

                vector<int> machine_list(machine_count, 0);
                vector<int> time_list(machine_count, 0);
                vector<int> v_list(muti_machine_num, 0);

                int protimemax = 0;
                if (temp < 0) {
                    int machine, time;
                    for (int k = 0; k < abs(temp); ++k) {
                        stream1 >> machine >> time;
                    }
                    machine_list[machine - muti_machine_num] = 1;
                    time_list[machine - muti_machine_num] = time;
                    std::fill(v_list.begin(), v_list.end(), 1); //所有模式均可以被选择           
                    protimemax = time;
                }
                else {
                    for (int k = 0; k < temp; ++k) {
                        int machine, time;
                        stream1 >> machine >> time;
                        machine_list[machine - 1] = 1;
                        time_list[machine - 1] = time;
                        v_list[0] = 1;
                        if (protimemax < time)
                        {
                            protimemax = time;
                        }
                    }
                }
                M += protimemax;

                M_row.push_back(machine_list);
                T_row.push_back(time_list);
                V_row.push_back(v_list);
            }
            M_table.push_back(M_row);
            T_table.push_back(T_row);
            V_table.push_back(V_row);
        }
        std::cout << V_table[0][1][1] << endl;
        int JobNum = job_count;
        std::cout << job_count << endl;
        int MacNum = machine_count;
        vector<int> OpNum = procedure_count;

        // 开始定义决策变量
        IloNumVar C_max(env, 0, IloInfinity, ILOINT);
        IloNumVar E(env, 0, IloInfinity, ILOINT);
        //四维决策变量  每个工件每个工序是否选择机床k进行加工 
        IntVarMatrix4d X(env, JobNum);
        for (int i = 0; i < JobNum; i++)
        {
            X[i] = IntVarMatrix3d(env, procedure_count[i]);
            for (int j = 0; j < procedure_count[i]; j++)
            {
                X[i][j] = IntVarMatrix(env, MacNum);
                for (int k = 0; k < MacNum; k++)
                {
                    if (M_table[i][j][k] > 0)
                    {
                        X[i][j][k] = IloNumVarArray(env, muti_machine_num);
                        for (int v = 0; v < muti_machine_num; v++)
                        {
                            if (V_table[i][j][v] > 0)
                            {
                                X[i][j][k][v] = IloNumVar(env, 0, 1, ILOBOOL);
                                string str = "X[" + to_string(i) + "][" + to_string(j) + "][" + to_string(k) + "][" + to_string(v) + "]";
                                X[i][j][k][v].setName(str.c_str());
                            }
                        }
                    }
                }
            }
        }
        //两维决策变量  每个工件每个工序开始加工时间
        IntVarMatrix3d B(env, JobNum);
        for (int i = 0; i < JobNum; i++)
        {
            B[i] = IntVarMatrix(env, procedure_count[i]);
            for (int j = 0; j < procedure_count[i]; j++)
            {
                B[i][j] = IloNumVarArray(env, MacNum);
                for (int k = 0; k < MacNum; k++)
                {
                    B[i][j][k] = IloNumVar(env, 0, IloInfinity, ILOINT);
                    string str = "B[" + to_string(i) + "][" + to_string(j) + "][" + to_string(k) + "]";
                    B[i][j][k].setName(str.c_str());
                }
            }
        }

        //四维决策变量  机器上加工任务的排序问题
        IntVarMatrix4d Y(env, JobNum);
        for (int i = 0; i < JobNum; i++)
        {
            Y[i] = IntVarMatrix3d(env, procedure_count[i]);
            for (int j = 0; j < procedure_count[i]; j++)
            {
                Y[i][j] = IntVarMatrix(env, JobNum);
                for (int i1 = 0; i1 < JobNum; i1++)
                {
                    Y[i][j][i1] = IloNumVarArray(env, procedure_count[i1]);
                    for (int j1 = 0; j1 < procedure_count[i1]; j1++)
                    {
                        Y[i][j][i1][j1] = IloNumVar(env, 0, 1, ILOBOOL);
                        string str = "Y[" + to_string(i) + "][" + to_string(j) + "][" + to_string(i1) + "][" + to_string(j1) + "]";
                        Y[i][j][i1][j1].setName(str.c_str());
                    }
                }
            }
        }

        //接下来添加约束条件
        //首先添加约束条件（3-2）
        IloExpr Sum_X(env);
        for (int i = 0; i < JobNum; i++)
        {
            for (int j = 0; j < procedure_count[i]; j++)
            {
                Sum_X.clear();
                for (int k = 0; k < MacNum; k++)
                {
                    if (M_table[i][j][k] > 0)
                    {
                        for (int v = 0; v < muti_machine_num; v++)
                        {
                            if (V_table[i][j][v] > 0)
                            {
                                Sum_X += X[i][j][k][v];
                            }
                        }
                    }
                }
                model.add(Sum_X == 1);
            }
        }
        //添加约束条件（3-3）
        IloExpr Sum_Bij1(env);
        IloExpr Sum_Bijk(env);
        IloExpr Sum_Bij1k(env);
        for (int i = 0; i < JobNum; i++)
        {
            for (int j = 0; j < procedure_count[i] - 1; j++)
            {
                Sum_Bij1.clear();
                Sum_Bijk.clear();
                Sum_Bij1k.clear();
                for (int k = 0; k < MacNum; k++)
                {
                    if (M_table[i][j][k] > 0)
                    {
                        Sum_Bijk += B[i][j][k];
                        for (int v = 0; v < muti_machine_num; v++)
                        {
                            if (V_table[i][j][v] > 0)
                            {
                                Sum_Bij1 += X[i][j][k][v] * T_table[i][j][k] / (v + 1);
                            }
                        }
                    }
                    if (M_table[i][j + 1][k] > 0)
                    {
                        Sum_Bij1k += B[i][j + 1][k];
                    }
                }
                model.add(Sum_Bijk + Sum_Bij1 <= Sum_Bij1k);
            }
        }

        //添加约束条件(3-4)和(3-5)
        IloExpr Sum_Bij2(env);
        IloExpr Sum_Bij3(env);
        IloExpr Sum_Bij4(env);
        IloExpr Sum_Bij5(env);
        for (int i = 0; i < JobNum; i++)
        {
            for (int i1 = 0; i1 < JobNum; i1++)
            {
                if (i < i1)
                {
                    for (int j = 0; j < procedure_count[i]; j++)
                    {
                        for (int j1 = 0; j1 < procedure_count[i1]; j1++)
                        {
                            for (int k = 0; k < MacNum; k++)
                            {
                                if (M_table[i][j][k] > 0 && M_table[i1][j1][k] > 0)
                                {
                                    Sum_Bij2.clear();
                                    Sum_Bij3.clear();
                                    Sum_Bij4.clear();
                                    Sum_Bij5.clear();
                                    for (int v = 0; v < muti_machine_num; v++)
                                    {
                                        if (V_table[i][j][v] > 0)
                                        {
                                            Sum_Bij2 += X[i][j][k][v] * T_table[i][j][k] / (v + 1);
                                            Sum_Bij3 += X[i][j][k][v];
                                        }
                                    }

                                    for (int v1 = 0; v1 < muti_machine_num; v1++)
                                    {
                                        if (V_table[i1][j1][v1] > 0)
                                        {
                                            Sum_Bij4 += X[i1][j1][k][v1];
                                            Sum_Bij5 += X[i1][j1][k][v1] * T_table[i1][j1][k] / (v1 + 1);
                                        }
                                    }
                                    model.add(B[i][j][k] + Sum_Bij2 <= B[i1][j1][k] + M * (3 - Y[i][j][i1][j1] - Sum_Bij3 - Sum_Bij4));
                                    model.add(B[i1][j1][k] + Sum_Bij5 <= B[i][j][k] + M * (2 + Y[i][j][i1][j1] - Sum_Bij3 - Sum_Bij4));
                                }
                            }
                        }
                    }
                }
            }
        }
        //添加约束条件（3-6）
        IloExpr Sum_Bin1(env);
        IloExpr Sum_Bin1k(env);
        for (int i = 0; i < JobNum; i++)
        {
            Sum_Bin1.clear();
            Sum_Bin1k.clear();
            for (int k = 0; k < MacNum; k++)
            {
                if (M_table[i][procedure_count[i] - 1][k] > 0)
                {
                    for (int v = 0; v < muti_machine_num; v++)
                    {
                        if (V_table[i][procedure_count[i] - 1][v] > 0)
                        {
                            Sum_Bin1 += X[i][procedure_count[i] - 1][k][v] * T_table[i][procedure_count[i] - 1][k] / (v + 1);
                        }
                    }
                    Sum_Bin1k += B[i][procedure_count[i] - 1][k];
                }
            }

            model.add(Sum_Bin1k + Sum_Bin1 <= C_max);
        }
        //首先添加约束条件(3-7) 和 (3-8)
        IloExpr Sum_Bijk7(env);
        for (int i = 0; i < JobNum; i++)
        {
            for (int j = 0; j < procedure_count[i]; j++)
            {
                for (int k = 0; k < MacNum; k++)
                {
                    if (M_table[i][j][k] > 0)
                    {
                        Sum_Bijk7.clear();
                        for (int v = 0; v < muti_machine_num; v++)
                        {
                            if (V_table[i][j][v] > 0)
                            {
                                Sum_Bijk7 += X[i][j][k][v];
                            }
                        }
                        model.add(B[i][j][k] <= M * Sum_Bijk7);
                    }
                }
            }
        }

        IloExpr Sum_E(env);
        Sum_E.clear();
        for (int i = 0; i < JobNum; i++)
        {
            for (int j = 0; j < procedure_count[i]; j++)
            {
                for (int k = 0; k < MacNum; k++)
                {
                    if (M_table[i][j][k] > 0)
                    {
                        for (int v = 0; v < muti_machine_num; v++)
                        {
                            if (V_table[i][j][v] > 0)
                            {
                                Sum_E += X[i][j][k][v] * (v + 1);
                            }
                        }
                    }
                }
                model.add(E >= Sum_E);
            }
        }

        model.add(IloMinimize(env, 0.9 * C_max + 0.1 * E));
        //创建求解对象
        IloCplex cplex(model);
        cplex.exportModel("model.lp");
        cplex.setParam(IloCplex::Threads, 20);
        cplex.setParam(IloCplex::Param::TimeLimit, 600);
        try {
            double starttime = clock();
            if (!cplex.solve())
            {
                std::cout << "求解失败" << endl;
                if ((cplex.getStatus() == IloAlgorithm::Infeasible) ||
                    (cplex.getStatus() == IloAlgorithm::InfeasibleOrUnbounded))
                {
                    std::cout << endl << "No solution - starting Conflict refinement" << endl;
                }

                env.error() << "Failed to optimize LP." << endl;
                throw(-1);
            }
            double spend_time = (clock() - starttime) / 1000;

            IloNumArray4 x_values(env, JobNum);
            for (int i = 0; i < JobNum; i++) {
                x_values[i] = IloNumArray3(env, procedure_count[i]);
                for (int j = 0; j < procedure_count[i]; j++) {
                    x_values[i][j] = IloNumArray2(env, MacNum);
                    for (int k = 0; k < MacNum; k++) {
                        if (M_table[i][j][k] > 0) {
                            x_values[i][j][k] = IloNumArray(env, muti_machine_num);
                            for (int v = 0; v < muti_machine_num; v++) {
                                if (V_table[i][j][v] > 0) {
                                    x_values[i][j][k][v] = cplex.getValue(X[i][j][k][v]);
                                }
                            }
                        }
                    }
                }
            }
            vector<vector<tuple<int, int, int, int>>> machine_table(MacNum);
            for (int i = 0; i < JobNum; i++) {
                for (int j = 0; j < procedure_count[i]; j++) {
                    for (int k = 0; k < MacNum; k++) {
                        if (M_table[i][j][k] > 0) {
                            for (int v = 0; v < muti_machine_num; v++) {
                                if (x_values[i][j][k][v] > 0) {
                                    int start_time = cplex.getValue(B[i][j][k]);
                                    int end_time = start_time + T_table[i][j][k] / (v + 1);
                                    machine_table[k].push_back({ i, j, start_time, end_time });
                                }
                            }
                        }
                    }
                }
            }

            std::ofstream file_writer(savepath + file.substr(0, file.size() - 4) + ".txt");
            file_writer << JobNum << " " << machine_count - 1 + muti_machine_num << " " << cplex.getObjValue() << " " << muti_machine_num << std::endl;

            for (int i = 0; i < MacNum; ++i) {
                file_writer << machine_table[i].size() << " ";
                for (const auto& operation : machine_table[i]) {
                    file_writer << std::get<0>(operation) << " " << std::get<1>(operation) << " ";
                }
                for (const auto& operation : machine_table[i]) {
                    file_writer << std::get<2>(operation) << " " << std::get<3>(operation) << " ";
                }
                file_writer << std::endl;
            }
            file_writer.close();

            int cmax = 0;
            cmax = cplex.getValue(C_max);
            env.out() << "Solution status = " << cmax << endl;
            env.out() << "Solution value = " << cplex.getMIPRelativeGap() << endl;
            env.out() << "Solution bound = " << cplex.getBestObjValue() << endl;
            env.out() << "Solution time = " << spend_time << endl;

            size_t lastDotPosition = file.find_last_of('.');
            string filenameWithoutExtension = file.substr(0, lastDotPosition);

            save_data.emplace_back(filenameWithoutExtension, cmax, cplex.getMIPRelativeGap(), cplex.getBestObjValue(), spend_time);
            /*           printf("结束");
                       system("pause");*/
        }
        catch (IloException& e)
        {
            cerr << "Concert exception caught: " << e << endl;
            //save results
        }
        catch (...)
        {
            cerr << "Unknown exception caught" << endl;
        }
        env.end();
    }

    auto currentTime = std::chrono::system_clock::now();
    std::time_t currentTimeT = std::chrono::system_clock::to_time_t(currentTime);
    std::tm localTime;
    if (localtime_s(&localTime, &currentTimeT) != 0) {
        std::cerr << "获取本地时间失败。\n";
        return 1; // Return an error code
    }

    // 打开输出文件
    std::ofstream outputFile;
    outputFile.open("./save_data/" + std::to_string(localTime.tm_year + 1900) + std::to_string(localTime.tm_mon + 1) + std::to_string(localTime.tm_mday)
        + std::to_string(localTime.tm_hour) + std::to_string(localTime.tm_min) + "save_hdata.csv");

    // 检查文件是否成功打开
    if (outputFile.is_open()) {
        // 将数据写入文件
        for (const auto& tuple : save_data) {
            outputFile << std::get<0>(tuple) << ","
                << std::get<1>(tuple) << ","
                << std::get<2>(tuple) << ","
                << std::get<3>(tuple) << ","
                << std::get<4>(tuple) << "\n";
        }

        // 关闭文件
        outputFile.close();
    }
    else {
        std::cerr << "无法打开输出文件。\n";
    }
    return 0;
}