"""
Logic vòng loại trực tiếp (knockout):
- Lấy top N đội từ mỗi bảng
- Tự động ghép đôi theo trình tự
- Sinh vòng tứ kết → bán kết → chung kết
"""

class KnockoutLogic:
    @staticmethod
    def generate_knockout_matches(bang_xep_hang_dict, so_doi_di_tiep=2, so_san=2):
        """
        bang_xep_hang_dict: {
            "Bảng A": [
                {"ten": "Team A", "diem": 3, "hieu_so": 5, ...},
                {"ten": "Team B", "diem": 2, "hieu_so": 1, ...},
                ...
            ],
            "Bảng B": [...],
            ...
        }
        
        Trả về: {
            "Tứ kết": [...matches...],
            "Bán kết": [...matches...],
            "Chung kết": [...matches...]
        }
        """
        # Lấy top N đội từ mỗi bảng
        qualified_teams = []
        for bang_name, xep_hang in bang_xep_hang_dict.items():
            top_n = xep_hang[:so_doi_di_tiep]
            for doi in top_n:
                qualified_teams.append({
                    "ten": doi["ten"],
                    "bang": bang_name,
                    "diem": doi.get("diem", 0),
                    "hieu_so": doi.get("hieu_so", 0)
                })
        
        # Sắp xếp theo điểm (cao nhất trước)
        qualified_teams.sort(key=lambda x: (-x["diem"], -x["hieu_so"]))
        
        # Sinh các vòng dựa vào số đội
        total_teams = len(qualified_teams)
        knockout_structure = {}
        
        if total_teams == 2:
            # Chỉ có chung kết
            knockout_structure["Chung kết"] = [
                {"doi_a": qualified_teams[0]["ten"], "doi_b": qualified_teams[1]["ten"], "san": 1}
            ]
        elif total_teams == 4:
            # Tứ kết → Chung kết
            tu_ket = [
                {"doi_a": qualified_teams[0]["ten"], "doi_b": qualified_teams[3]["ten"], "san": 1},
                {"doi_a": qualified_teams[1]["ten"], "doi_b": qualified_teams[2]["ten"], "san": 2 if so_san >= 2 else 1}
            ]
            knockout_structure["Tứ kết"] = tu_ket
            # Ban ket sẽ sinh sau khi có kết quả tứ kết
            knockout_structure["Ban kết"] = []
            knockout_structure["Chung kết"] = []
        elif total_teams == 6:
            # 2 trận tứ kết (top 2 vs bottom 2, next 2 vs next-bottom 2)
            tu_ket = [
                {"doi_a": qualified_teams[0]["ten"], "doi_b": qualified_teams[5]["ten"], "san": 1},
                {"doi_a": qualified_teams[1]["ten"], "doi_b": qualified_teams[4]["ten"], "san": 2 if so_san >= 2 else 1},
                {"doi_a": qualified_teams[2]["ten"], "doi_b": qualified_teams[3]["ten"], "san": 1 if so_san == 1 else (3 if so_san >= 3 else 2)}
            ]
            knockout_structure["Tứ kết"] = tu_ket
            knockout_structure["Ban kết"] = []
            knockout_structure["Chung kết"] = []
        elif total_teams == 8:
            # 4 trận tứ kết toàn bộ
            tu_ket = [
                {"doi_a": qualified_teams[0]["ten"], "doi_b": qualified_teams[7]["ten"], "san": 1},
                {"doi_a": qualified_teams[1]["ten"], "doi_b": qualified_teams[6]["ten"], "san": 2 if so_san >= 2 else 1},
                {"doi_a": qualified_teams[2]["ten"], "doi_b": qualified_teams[5]["ten"], "san": 3 if so_san >= 3 else (1 if so_san == 1 else 2)},
                {"doi_a": qualified_teams[3]["ten"], "doi_b": qualified_teams[4]["ten"], "san": 4 if so_san >= 4 else (2 if so_san >= 2 else 1)}
            ]
            knockout_structure["Tứ kết"] = tu_ket
            knockout_structure["Ban kết"] = []
            knockout_structure["Chung kết"] = []
        
        return knockout_structure, qualified_teams

    @staticmethod
    def generate_next_round(current_round_matches, round_name):
        """
        Tính toán vòng tiếp theo dựa vào kết quả vòng hiện tại.
        Chỉ làm được khi tất cả trận trong vòng hiện tại đã xong.
        """
        # Sắp xếp thắng thua
        winners = []
        for match in current_round_matches:
            if match['diem_a'] is None or match['diem_b'] is None:
                return None  # Chưa xong hết
            if match['diem_a'] > match['diem_b']:
                winners.append(match['doi_a'])
            else:
                winners.append(match['doi_b'])
        
        if not winners:
            return []
        
        # Nếu chỉ còn 1 người → là chung kết
        if len(winners) == 1:
            return []
        
        # Ghép cặp thắng lại
        next_matches = []
        for i in range(0, len(winners), 2):
            if i + 1 < len(winners):
                next_matches.append({
                    "doi_a": winners[i],
                    "doi_b": winners[i + 1],
                    "san": (i // 2) + 1
                })
        
        return next_matches