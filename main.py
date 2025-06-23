from sso import API, LoginError
from urllib.parse import urlencode

def main():
    print("="*60)
    print("      欢迎使用北航自动评教工具")
    print("="*60)

    # 用户输入用户名和密码
    username = input("请输入学号: ").strip()
    password = input("请输入密码: ").strip()
    api = API(username, password)
    try:
        api.login()
        print("✅ 登录成功")
    except LoginError as e:
        print(f"❌ 登录失败: {e}")
        return
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return

    # 获取主页面
    resp = api.get("https://spoc.buaa.edu.cn/pjxt/cas")
    if resp.status_code != 200:
        print("❌ 无法访问主页面")
        return

    # 查询学期（待办）
    try:
        data = api.post("https://spoc.buaa.edu.cn/pjxt/component/queryDaiBan").json()
        if isinstance(data, list) and data:
            dbywsm = data[0].get('dbywsm', '未知学期')
            print(f"当前评教学期: {dbywsm}")
        else:
            print("当前没有待评教课程")
            cont = input("是否继续？(y/n): ").strip().lower()
            if cont != 'y':
                return
    except Exception:
        print("❌ 学期查询失败")

    # 获取学期信息
    try:
        xnxq_data = api.post("https://spoc.buaa.edu.cn/pjxt/component/queryXnxq").json()
        first_term = xnxq_data["content"][0]
        xnxq = f"{first_term['xn']}{first_term['xq']}"
        print(f"学期: {xnxq}")
    except Exception:
        print("❌ 学期信息获取失败")
        return

    # 获取评教任务
    try:
        url = f"https://spoc.buaa.edu.cn/pjxt/personnelEvaluation/listObtainPersonnelEvaluationTasks?yhdm={username}&rwmc=&sfyp=0&pageNum=1&pageSize=10"
        tasks = api.get(url).json()
        rwid = tasks["result"]["list"][0].get("rwid")
        rwmc = tasks["result"]["list"][0].get("rwmc", "未知任务")
        print(f"任务: {rwmc}")
    except Exception:
        print("❌ 评教任务获取失败")
        return

    # 获取问卷列表
    try:
        url = f"https://spoc.buaa.edu.cn/pjxt/evaluationMethodSix/getQuestionnaireListToTask?rwid={rwid}&sfyp=0&pageNum=1&pageSize=999"
        response = api.get(url)
        print(f"📥 获取问卷列表返回状态码: {response.status_code}")
        wj_list = response.json().get("result", [])
        print("问卷列表:")
        for item in wj_list:
            wjmc = item.get("wjmc", "未知问卷")
            rwmc = item.get("rwmc", "未知任务")
            print(f"  - 问卷: {wjmc}, 任务: {rwmc}")
    except Exception as e:
        print(f"❌ 问卷列表获取失败: {e}")
        return

    # 获取所有课程
    all_courses = []
    for wj in wj_list:
        try:
            wjid = wj["wjid"]
            wjmc = wj.get("wjmc", "未知问卷")
            rwmc = wj.get("rwmc", "未知任务")
            msid = wj.get("msid", "1")
            api.post("https://spoc.buaa.edu.cn/pjxt/evaluationMethodSix/reviseQuestionnairePattern", json={
                "rwid": rwid, "wjid": wjid, "msid": msid
            })
            url = f"https://spoc.buaa.edu.cn/pjxt/evaluationMethodSix/getRequiredReviewsData?sfyp=0&wjid={wjid}&xnxq={xnxq}&pageNum=1&pageSize=999"
            response = api.get(url)
            print(f"📥 获取课程返回状态码: {response.status_code}")
            courses = response.json().get("result", [])
            for course in courses:
                kcmc = course.get("kcmc", "未知课程")
                bpmc = course.get("bpmc", "未知教师")  # 修正为从 bpmc 提取教师名称
                print(f"  - 课程: {kcmc}, 教师: {bpmc}")
            all_courses.extend(courses)
            print(f"问卷 {wjmc} - {rwmc} 课程数: {len(courses)}")
        except Exception as e:
            print(f"❌ 问卷 {wjmc} - {rwmc} 课程获取失败: {e}")

    print(f"总课程数: {len(all_courses)}")

    # 评教并提交
    for course in all_courses:
        kcmc = course.get("kcmc", "未知课程")
        bpmc = course.get("bpmc", "未知教师")  # 修正为从 bpmc 提取教师名称
        wjid = course.get("wjid")
        print(f"📋 当前课程: 课程：{kcmc}, 教师：{bpmc}")  # 添加日志输出
        if not wjid:
            print(f"❌ 课程 {kcmc} - {bpmc} 无问卷ID")
            continue
        payload = {
            "id": "",
            "rwid": course.get("rwid"),
            "wjid": wjid,
            "zdmc": course.get("zdmc", "STID"),
            "ypjcs": course.get("ypjcs", 0),
            "xypjcs": course.get("xypjcs", 1),
            "sxz": course.get("sxz"),
            "pjrdm": course.get("pjrdm"),
            "pjrmc": course.get("pjrmc"),
            "bpdm": course.get("bpdm"),
            "bpmc": course.get("bpmc"),
            "kcdm": course.get("kcdm"),
            "kcmc": course.get("kcmc"),
            "rwh": course.get("rwh"),
            "xn": course.get("xn", ""),
            "xq": course.get("xq", ""),
            "xnxq": course.get("xnxq"),
            "pjlxid": course.get("pjlxid", "2"),
            "sfksqbpj": course.get("sfksqbpj", "1"),
            "yxsfktjst": course.get("yxsfktjst", ""),
            "yxdm": ""
        }
        url = "https://spoc.buaa.edu.cn/pjxt/evaluationMethodSix/getQuestionnaireTopic?" + urlencode(payload)
        try:
            response = api.get(url)
            q_data = response.json()
            if q_data.get("code") != "200":
                print(f"❌ 问卷 {kcmc} - {bpmc} 获取失败")
                continue
            result = q_data.get("result", [])
            if not result:
                print(f"❌ 问卷 {kcmc} - {bpmc} 无题目")
                continue
            wj_entity = result[0].get("pjxtWjWjbReturnEntity", {})
            wjzblist = wj_entity.get("wjzblist", [])
            all_questions = [q for zb in wjzblist for q in zb.get("tklist", [])]
            pjjglist = []
            for pjjg in result[0].get("pjxtPjjgPjjgckb", []):
                pjxxlist = []
                for q in all_questions:
                    tmlx = q.get("tmlx", "1")
                    tmxxlist = q.get("tmxxlist", [])
                    if tmlx == "1":
                        xxid = tmxxlist[1]["tmxxid"] if len(tmxxlist) > 1 else (tmxxlist[0]["tmxxid"] if tmxxlist else "")
                        xxdalist = [xxid] if xxid else []
                    elif tmlx == "6":
                        xxdalist = []
                    else:
                        xxdalist = []
                    pjxxlist.append({
                        "sjly": "1",
                        "stlx": tmlx,
                        "wjid": wjid,
                        "wjssrwid": pjjg.get("wjssrwid"),
                        "wjstctid": tmxxlist[0]["tmxxid"] if tmlx == "6" and tmxxlist else "",
                        "wjstid": q.get("tmid"),
                        "xxdalist": xxdalist
                    })
                pjjglist.append({
                    "bprdm": pjjg.get("bprdm"),
                    "bprmc": pjjg.get("bprmc"),
                    "kcdm": pjjg.get("kcdm"),
                    "kcmc": pjjg.get("kcmc"),
                    "pjdf": 93,
                    "pjfs": pjjg.get("pjfs", "1"),
                    "pjid": pjjg.get("pjid"),
                    "pjlx": pjjg.get("pjlx"),
                    "pjmap": result[0].get("pjmap"),
                    "pjrdm": pjjg.get("pjrdm"),
                    "pjrjsdm": pjjg.get("pjrjsdm"),
                    "pjrxm": pjjg.get("pjrxm"),
                    "pjsx": 1,
                    "pjxxlist": pjxxlist,
                    "rwh": pjjg.get("rwh"),
                    "stzjid": "xx",
                    "wjid": wjid,
                    "wjssrwid": pjjg.get("wjssrwid"),
                    "wtjjy": "",
                    "xhgs": None,
                    "xnxq": pjjg.get("xnxq"),
                    "sfxxpj": pjjg.get("sfxxpj", "1"),
                    "sqzt": None,
                    "yxfz": None,
                    "zsxz": pjjg.get("pjrjsdm", ""),
                    "sfnm": "1"
                })
            if not pjjglist:
                print(f"❌ 问卷 {kcmc} - {bpmc} 无评教对象")
                continue
            submit_payload = {
                "pjidlist": [],
                "pjjglist": pjjglist,
                "pjzt": "1"
            }
            resp = api.post("https://spoc.buaa.edu.cn/pjxt/evaluationMethodSix/submitSaveEvaluation", json=submit_payload)
            result = resp.json()
            if result.get("code") == "200":
                print(f"✅ 问卷 {kcmc} - {bpmc} 提交成功")
            else:
                print(f"❌ 问卷 {kcmc} - {bpmc} 提交失败，可能已评教")
        except Exception as e:
            print(f"❌ 问卷 {kcmc} - {bpmc} 处理异常: {e}")

if __name__ == '__main__':
    main()
    input("\n程序已结束，按回车键退出...")