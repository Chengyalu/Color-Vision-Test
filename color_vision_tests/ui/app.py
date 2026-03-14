from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import Image, ImageTk, ImageOps, ImageDraw

from color_vision_tests.io import export_csv
from color_vision_tests.scoring import arrangement_summary, score_hrr
from color_vision_tests.tests import D15Test, FMD15Test, HRRTest


class ArrangementFrame(ttk.Frame):
    CAP_W = 58
    CAP_H = 58
    GAP = 16

    TOP_Y = 110
    BOTTOM_Y = 255

    TOP_START_X = 150
    BOTTOM_START_X = 110

    HIGHLIGHT_COLOR = "#4da3ff"

    def __init__(self, master, test_factory, participant_getter, output_dir: Path):
        super().__init__(master, padding=12)
        self.test_factory = test_factory
        self.participant_getter = participant_getter
        self.output_dir = output_dir
        self.test = self.test_factory()

        # 上排待做色块：元素为 order_value；拖到下排后位置变为 None
        self.pool_order: list[int | None] = []
        # 下排固定 15 个槽位：元素为 order_value 或 None
        self.placed_order: list[int | None] = []

        self.top_items: list[dict] = []
        self.bottom_items: list[dict] = []

        # 拖拽状态：
        # {
        #   "source": "top" | "bottom",
        #   "order_value": int,
        #   "rect": canvas_id,
        #   "orig_coords": (x1,y1,x2,y2),
        #   "mouse_start": (x,y),
        #   "source_index": int,
        # }
        self.drag_data: dict | None = None
        self.drop_highlight_id: int | None = None

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text=self.test.name, font=("Arial", 16, "bold")).pack(side="left")
        ttk.Button(header, text="Start Test", command=self.reset_test).pack(side="right", padx=4)
        ttk.Button(header, text="Save Result", command=self.save_result).pack(side="right", padx=4)

        self.canvas = tk.Canvas(
            self,
            width=1360,
            height=520,
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.summary_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.summary_var, justify="left").pack(anchor="w", pady=(8, 0))

        self.reset_test()

    def reset_test(self):
        self.test = self.test_factory()
        self.test.start()

        self.pool_order = [i for i in self.test.shuffled_order if i != self.test.anchor_index]
        self.placed_order = [None] * (len(self.test.colors) - 1)

        self.drag_data = None
        self.drop_highlight_id = None

        self.redraw_all()
        self.update_summary()

    def top_slot_coords(self, idx: int):
        x1 = self.TOP_START_X + idx * (self.CAP_W + self.GAP)
        y1 = self.TOP_Y
        x2 = x1 + self.CAP_W
        y2 = y1 + self.CAP_H
        return x1, y1, x2, y2

    def bottom_slot_coords(self, idx: int):
        x1 = self.BOTTOM_START_X + (idx + 1) * (self.CAP_W + self.GAP)
        y1 = self.BOTTOM_Y
        x2 = x1 + self.CAP_W
        y2 = y1 + self.CAP_H
        return x1, y1, x2, y2

    def redraw_all(self):
        self.canvas.delete("all")
        self.top_items.clear()
        self.bottom_items.clear()
        self.drop_highlight_id = None

        # 上排待做色块
        for i, order_value in enumerate(self.pool_order):
            if order_value is None:
                continue

            x1, y1, x2, y2 = self.top_slot_coords(i)
            rect = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=self.rgb_to_hex(self.test.colors[order_value]),
                outline="black",
                width=2,
            )
            item = {
                "rect": rect,
                "order_value": order_value,
                "index": i,
                "home": (x1, y1, x2, y2),
            }
            self.top_items.append(item)

            self.canvas.tag_bind(rect, "<ButtonPress-1>", self.on_top_press)
            self.canvas.tag_bind(rect, "<B1-Motion>", self.on_drag_motion)
            self.canvas.tag_bind(rect, "<ButtonRelease-1>", self.on_drag_release)

        # 下排 anchor
        anchor_rgb = self.test.colors[self.test.anchor_index]
        ax1 = self.BOTTOM_START_X
        ay1 = self.BOTTOM_Y
        ax2 = ax1 + self.CAP_W
        ay2 = ay1 + self.CAP_H
        self.canvas.create_rectangle(
            ax1, ay1, ax2, ay2,
            fill=self.rgb_to_hex(anchor_rgb),
            outline="black",
            width=2,
        )

        # 下排固定 15 个槽位背景
        for i in range(len(self.placed_order)):
            x1, y1, x2, y2 = self.bottom_slot_coords(i)
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill="#f2f2f2",
                outline="black",
                width=2,
            )

        # 下排已放置色块
        for i, order_value in enumerate(self.placed_order):
            if order_value is None:
                continue

            x1, y1, x2, y2 = self.bottom_slot_coords(i)
            rect = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=self.rgb_to_hex(self.test.colors[order_value]),
                outline="black",
                width=2,
            )
            item = {
                "rect": rect,
                "order_value": order_value,
                "slot_index": i,
                "home": (x1, y1, x2, y2),
            }
            self.bottom_items.append(item)

            self.canvas.tag_bind(rect, "<ButtonPress-1>", self.on_bottom_press)
            self.canvas.tag_bind(rect, "<B1-Motion>", self.on_drag_motion)
            self.canvas.tag_bind(rect, "<ButtonRelease-1>", self.on_drag_release)

        self.canvas.create_text(
            680, 390,
            text="Arrange the color caps in hue order by dragging them into the empty slots below",
            fill="white",
            font=("Arial", 24),
        )

    def find_top_item_by_rect(self, rect_id):
        for item in self.top_items:
            if item["rect"] == rect_id:
                return item
        return None

    def find_bottom_item_by_rect(self, rect_id):
        for item in self.bottom_items:
            if item["rect"] == rect_id:
                return item
        return None

    def on_top_press(self, event):
        item_id = self.canvas.find_withtag("current")
        if not item_id:
            return
        item = self.find_top_item_by_rect(item_id[0])
        if item is None:
            return

        x1, y1, x2, y2 = self.canvas.coords(item["rect"])
        self.drag_data = {
            "source": "top",
            "order_value": item["order_value"],
            "rect": item["rect"],
            "orig_coords": (x1, y1, x2, y2),
            "mouse_start": (event.x, event.y),
            "source_index": item["index"],
        }
        self.canvas.tag_raise(item["rect"])

    def on_bottom_press(self, event):
        item_id = self.canvas.find_withtag("current")
        if not item_id:
            return
        item = self.find_bottom_item_by_rect(item_id[0])
        if item is None:
            return

        x1, y1, x2, y2 = self.canvas.coords(item["rect"])
        self.drag_data = {
            "source": "bottom",
            "order_value": item["order_value"],
            "rect": item["rect"],
            "orig_coords": (x1, y1, x2, y2),
            "mouse_start": (event.x, event.y),
            "source_index": item["slot_index"],
        }
        self.canvas.tag_raise(item["rect"])

    def on_drag_motion(self, event):
        if not self.drag_data:
            return

        x1, y1, x2, y2 = self.drag_data["orig_coords"]
        sx, sy = self.drag_data["mouse_start"]
        dx = event.x - sx
        dy = event.y - sy

        self.canvas.coords(
            self.drag_data["rect"],
            x1 + dx, y1 + dy, x2 + dx, y2 + dy
        )

        slot_idx = self.find_empty_target_slot_under(event.x, event.y)
        self.show_slot_highlight(slot_idx)

    def on_drag_release(self, event):
        if not self.drag_data:
            return

        source = self.drag_data["source"]
        source_index = self.drag_data["source_index"]
        order_value = self.drag_data["order_value"]

        slot_idx = self.find_empty_target_slot_under(event.x, event.y)
        self.clear_drop_indicator()

        if slot_idx is not None:
            if source == "top":
                # 上排 -> 下排空槽
                self.placed_order[slot_idx] = order_value
                self.pool_order[source_index] = None

            elif source == "bottom":
                # 下排 -> 另一个空槽
                if slot_idx != source_index:
                    self.placed_order[slot_idx] = order_value
                    self.placed_order[source_index] = None
                # 如果释放时找不到空槽，或者还是本槽，都在下面统一 redraw 回原位
        else:
            # 没放到有效空槽，什么都不改
            pass

        self.drag_data = None
        self.redraw_all()
        self.update_summary()

    def find_empty_target_slot_under(self, x, y) -> int | None:
        """
        返回可投放的空槽：
        - 对上排色块：必须是空槽
        - 对下排色块：必须是空槽，原槽位不算目标槽
        """
        for i in range(len(self.placed_order)):
            x1, y1, x2, y2 = self.bottom_slot_coords(i)
            if not (x1 <= x <= x2 and y1 <= y <= y2):
                continue

            if self.drag_data is None:
                return None

            if self.drag_data["source"] == "top":
                if self.placed_order[i] is None:
                    return i
                return None

            if self.drag_data["source"] == "bottom":
                source_index = self.drag_data["source_index"]
                if i == source_index:
                    return None
                if self.placed_order[i] is None:
                    return i
                return None

        return None

    def show_slot_highlight(self, slot_idx: int | None):
        self.clear_drop_indicator()
        if slot_idx is None:
            return

        x1, y1, x2, y2 = self.bottom_slot_coords(slot_idx)
        self.drop_highlight_id = self.canvas.create_rectangle(
            x1 - 3, y1 - 3, x2 + 3, y2 + 3,
            outline=self.HIGHLIGHT_COLOR,
            width=3,
        )

    def clear_drop_indicator(self):
        if self.drop_highlight_id is not None:
            self.canvas.delete(self.drop_highlight_id)
            self.drop_highlight_id = None

    def get_response_order(self):
        # anchor + 下排从左到右已放置的色块；空槽忽略
        response = [self.test.anchor_index]
        for value in self.placed_order:
            if value is not None:
                response.append(value)
        return response

    def update_summary(self):
        placed_count = sum(v is not None for v in self.placed_order)
        response = self.get_response_order()

        if len(response) <= 1:
            self.summary_var.set("Sorting not completed yet.")
            return

        result = arrangement_summary(
            response,
            coordinates=self.test.coordinates,
            calculated_max_radius=self.test.calculated_max_radius,
        )

        self.summary_var.set(
            f"Placed caps：{placed_count}    "
            f"C-INDEX: {result['C-INDEX']}    "
            f"TES: {result['TES']}    "
            f"S-INDEX: {result['S-INDEX']}"
        )
    

    def save_result(self):
        participant = self.participant_getter()
        if not participant["participant_id"]:
            messagebox.showwarning("Missing participant ID", "Please enter participant ID first.")
            return
        if not self.responses:
            messagebox.showwarning("No responses", "Please answer at least one plate first.")
            return

        total_score = sum(item["plate_score"] for item in self.responses)
        max_score = len(self.responses) * 2.0
        accuracy = total_score / max_score if max_score > 0 else 0.0

        rows = []
        for item in self.responses:
            rows.append({
                **participant,
                "test_name": "HRR",
                "plate_id": item["plate_id"],
                "correct_positions": " | ".join(item["correct_positions"]),
                "response_positions": " | ".join(item["response_positions"]),
                "correct_count": item["correct_count"],
                "plate_score": item["plate_score"],
                "total_score": "",
                "max_score": "",
                "accuracy": "",
            })

        rows.append({
            **participant,
            "test_name": "HRR_SUMMARY",
            "plate_id": "",
            "correct_positions": "",
            "response_positions": "",
            "correct_count": "",
            "plate_score": "",
            "total_score": total_score,
            "max_score": max_score,
            "accuracy": round(accuracy, 4),
        })

        filename = f"{participant['participant_id']}_HRR.csv"
        export_csv(self.output_dir / filename, rows)
        messagebox.showinfo("Saved", f"Result saved to outputs/{filename}")

    @staticmethod
    def rgb_to_hex(rgb):
        return "#%02x%02x%02x" % tuple(rgb)


class HRRFrame(ttk.Frame):
    SYMBOLS = ["circle", "cross", "triangle"]

    def __init__(self, master, participant_getter, output_dir: Path):
        super().__init__(master, padding=12)
        self.participant_getter = participant_getter
        self.output_dir = output_dir
        self.test = HRRTest.create_default()

        self.index = 0
        self.responses = []
        self.current_plate_photo = None
        self.current_symbol = "circle"
        self.mode = "study"   # "study" or "recall"

        # 四个格子的当前填写结果：top-left, top-right, bottom-left, bottom-right
        self.cell_values = ["blank", "blank", "blank", "blank"]
        self.cell_buttons = []
        self.icon_images = {}
        self.symbol_buttons = {}

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="HRR", font=("Arial", 16, "bold")).pack(side="left")
        ttk.Button(header, text="Restart", command=self.restart).pack(side="right")

        # header = ttk.Frame(self)
        # header.pack(fill="x", pady=(0, 10))
        # ttk.Label(header, text="HRR", font=("Arial", 16, "bold")).pack(side="left")
        # ttk.Button(header, text="Save Result", command=self.save_result).pack(side="right", padx=6)
        # ttk.Button(header, text="Restart", command=self.restart).pack(side="right")

        self.progress_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.progress_var).pack(anchor="w", pady=(0, 8))

        # 主区域
        self.main_area = tk.Frame(self, bg="#d9d9d9")
        self.main_area.pack(fill="both", expand=True, padx=10, pady=10)

        self.summary_var = tk.StringVar(value="No HRR response yet.")
        ttk.Label(self, textvariable=self.summary_var, justify="left").pack(anchor="w", pady=(8, 0))

        self.load_plate()

    def restart(self):
        self.index = 0
        self.responses = []
        self.current_symbol = "circle"
        self.mode = "study"
        self.summary_var.set("No HRR response yet.")
        self.load_plate()

    def clear_main_area(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

        # 固定三列布局，避免 study / recall 切换时整体位置跳动
        self.stage_frame = tk.Frame(self.main_area, bg="#d9d9d9")
        self.stage_frame.pack(expand=True)

        self.left_stage = tk.Frame(self.stage_frame, bg="#d9d9d9", width=220, height=420)
        self.left_stage.grid(row=0, column=0, padx=(20, 16), pady=20)
        self.left_stage.grid_propagate(False)

        self.center_stage = tk.Frame(self.stage_frame, bg="#d9d9d9", width=620, height=420)
        self.center_stage.grid(row=0, column=1, padx=0, pady=20)
        self.center_stage.grid_propagate(False)

        self.right_stage = tk.Frame(self.stage_frame, bg="#d9d9d9", width=160, height=420)
        self.right_stage.grid(row=0, column=2, padx=(16, 20), pady=20)
        self.right_stage.grid_propagate(False)

    def make_placeholder(self, text: str, size=(500, 360)):
        img = Image.new("RGB", size, (235, 235, 235))
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), text, fill=(0, 0, 0))
        return img

    def load_icon(self, logical_name: str, size=(72, 72)):
        mapping = {
            "circle": ["圆", "circle"],
            "cross": ["叉", "cross"],
            "triangle": ["三角", "triangle"],
            "next": ["进", "next"],
            "ready": ["准备", "ready"],
        }

        for stem in mapping.get(logical_name, []):
            p = self.test.find_icon_path(stem)
            if p is not None and p.exists():
                img = Image.open(p).convert("RGBA")
                img = ImageOps.contain(img, size)
                return ImageTk.PhotoImage(img)

        img = self.make_placeholder(logical_name, size=size)
        img = ImageOps.contain(img, size)
        return ImageTk.PhotoImage(img)

    def get_plate_photo(self, plate):
        path = self.test.get_image_path(plate)
        if path.exists():
            img = Image.open(path).convert("RGB")
        else:
            img = self.make_placeholder(f"Missing image:\n{path.name}", size=(500, 360))
        img = ImageOps.contain(img, (500, 360))
        return ImageTk.PhotoImage(img)

    def load_plate(self):
        self.clear_main_area()

        if self.index >= len(self.test.plates):
            self.progress_var.set("All plates completed.")

            done = tk.Label(
                self.center_stage,
                text="All plates completed.",
                font=("Arial", 18, "bold"),
                bg="#d9d9d9",
            )
            done.place(relx=0.5, rely=0.40, anchor="center")

            save_btn = tk.Button(
                self.center_stage,
                text="Save Result",
                font=("Arial", 12, "bold"),
                width=12,
                height=2,
                command=self.save_result,
                bg="white",
                relief="solid",
                bd=1,
            )
            save_btn.place(relx=0.5, rely=0.58, anchor="center")

            return

        self.mode = "study"
        self.current_symbol = "circle"
        self.cell_values = ["blank", "blank", "blank", "blank"]

        plate = self.test.plates[self.index]
        self.progress_var.set(f"Plate {self.index + 1} / {len(self.test.plates)}: {plate.plate_id}")

        # 中间固定放测试图
        plate_outer = tk.Frame(self.center_stage, bg="#8f8f8f", padx=18, pady=18)
        plate_outer.place(relx=0.5, rely=0.5, anchor="center")

        plate_inner = tk.Frame(plate_outer, bg="#bdbdbd", padx=18, pady=18)
        plate_inner.pack()

        self.current_plate_photo = self.get_plate_photo(plate)
        plate_label = tk.Label(plate_inner, image=self.current_plate_photo, bg="#bdbdbd")
        plate_label.pack()

        # 右边固定放 Ready
        ready_btn = tk.Button(
            self.right_stage,
            text="Ready",
            font=("Arial", 12, "bold"),
            width=8,
            height=4,
            command=self.start_recall,
            bg="white",
            relief="solid",
            bd=1,
        )
        ready_btn.place(relx=0.5, rely=0.5, anchor="center")

    def start_recall(self):
        if self.index >= len(self.test.plates):
            return

        self.clear_main_area()
        self.mode = "recall"
        self.current_symbol = "circle"
        self.cell_values = ["blank", "blank", "blank", "blank"]

        # 左边固定放图标列
        icon_panel = tk.Frame(self.left_stage, bg="#8f8f8f", padx=10, pady=10)
        icon_panel.place(relx=0.5, rely=0.5, anchor="center")

        self.symbol_buttons = {}
        for sym in self.SYMBOLS:
            if sym not in self.icon_images:
                self.icon_images[sym] = self.load_icon(sym, size=(72, 72))

            btn = tk.Button(
                icon_panel,
                image=self.icon_images[sym],
                command=lambda s=sym: self.select_symbol(s),
                relief="solid",
                bd=1,
                bg="white",
                activebackground="#d9ecff",
                width=82,
                height=82,
            )
            btn.pack(pady=6)
            self.symbol_buttons[sym] = btn

        cell_size = 200
        grid_total = cell_size * 2 + 2  # 2列 + 中间线条效果

        grid_outer = tk.Frame(
            self.center_stage,
            bg="#8f8f8f",
            width=grid_total + 40,
            height=grid_total + 40,
        )
        grid_outer.place(relx=0.5, rely=0.5, anchor="center")
        grid_outer.pack_propagate(False)
        grid_outer.grid_propagate(False)

        grid_frame = tk.Frame(
            grid_outer,
            bg="#f0f0f0",
            width=grid_total,
            height=grid_total,
            relief="solid",
            bd=1,
        )
        grid_frame.place(relx=0.5, rely=0.5, anchor="center")
        grid_frame.pack_propagate(False)
        grid_frame.grid_propagate(False)

        self.cell_buttons = []

        for idx in range(4):
            cell_wrapper = tk.Frame(
                grid_frame,
                width=cell_size,
                height=cell_size,
                bg="#f3f3f3",
                relief="solid",
                bd=1,
            )
            cell_wrapper.grid(row=idx // 2, column=idx % 2, padx=0, pady=0)
            cell_wrapper.grid_propagate(False)
            cell_wrapper.pack_propagate(False)

            btn = tk.Button(
                cell_wrapper,
                text="",
                bg="#f3f3f3",
                relief="flat",
                bd=0,
                highlightthickness=0,
                activebackground="#f3f3f3",
                command=lambda i=idx: self.place_symbol(i),
            )
            btn.pack(fill="both", expand=True)

            self.cell_buttons.append(btn)

      

        # 右边固定放 Next
        if "next" not in self.icon_images:
            self.icon_images["next"] = self.load_icon("next", size=(72, 72))

        next_btn = tk.Button(
            self.right_stage,
            image=self.icon_images["next"],
            command=self.submit_current,
            relief="solid",
            bd=1,
            bg="white",
            width=82,
            height=82,
        )
        next_btn.place(relx=0.5, rely=0.5, anchor="center")

        self.update_symbol_highlight()
        self.refresh_cells()
    def select_symbol(self, symbol: str):
        if self.mode != "recall":
            return
        self.current_symbol = symbol
        self.update_symbol_highlight()

    def update_symbol_highlight(self):
        for sym, btn in self.symbol_buttons.items():
            if sym == self.current_symbol:
                btn.config(bg="#d9ecff")
            else:
                btn.config(bg="white")

    def refresh_cells(self):
        for idx, value in enumerate(self.cell_values):
            btn = self.cell_buttons[idx]
            btn.config(image="", text="", compound="center", bg="#f3f3f3")

            if value == "blank":
                btn.config(text="")
            else:
                # 给网格里的答案图标单独开缓存，尺寸更大
                cache_key = f"{value}_cell_large"
                if cache_key not in self.icon_images:
                    self.icon_images[cache_key] = self.load_icon(value, size=(140, 140))
                btn.config(image=self.icon_images[cache_key])

    def place_symbol(self, idx: int):
        if self.mode != "recall":
            return
        self.cell_values[idx] = self.current_symbol
        self.refresh_cells()

    def submit_current(self):
        if self.mode != "recall":
            return
        if self.index >= len(self.test.plates):
            return

        plate = self.test.plates[self.index]
        response_positions = self.cell_values[:]

        correct_count = sum(
            1 for c, r in zip(plate.positions, response_positions) if c == r
        )

        # 评分规则：全对2分，部分对0.5分，全错0分
        if correct_count == 4:
            plate_score = 2.0
        elif correct_count > 0:
            plate_score = 0.5
        else:
            plate_score = 0.0

        self.responses.append(
            {
                "plate_id": plate.plate_id,
                "correct_positions": plate.positions,
                "response_positions": response_positions,
                "correct_count": correct_count,
                "plate_score": plate_score,
            }
        )

        self.index += 1
        self.load_plate()

        total_score = sum(item["plate_score"] for item in self.responses)
        accuracy = total_score / (len(self.responses) * 2.0) if self.responses else 0.0
        self.summary_var.set(
            f"Answered: {len(self.responses)}\n"
            f"Total score: {total_score}\n"
            f"Max score: {len(self.responses) * 2.0}\n"
            f"Accuracy: {accuracy:.1%}"
        )

    def save_result(self):
        participant = self.participant_getter()
        if not participant["participant_id"]:
            messagebox.showwarning("Missing participant ID", "Please enter participant ID first.")
            return
        if not self.responses:
            messagebox.showwarning("No responses", "Please answer at least one plate first.")
            return

        total_score = sum(item["plate_score"] for item in self.responses)
        total_plates = len(self.responses)
        max_score = total_plates * 2.0

        rows = []
        for item in self.responses:
            rows.append({
                **participant,
                "test_name": "HRR",
                "plate_id": item["plate_id"],
                "correct_positions": " | ".join(item["correct_positions"]),
                "response_positions": " | ".join(item["response_positions"]),
                "correct_count": item["correct_count"],
                "plate_score": item["plate_score"],
                "HRR_total_score": "",
                "HRR_max_score": "",
            })

        # 最后一行单独保存总分
        rows.append({
            **participant,
            "test_name": "HRR_SUMMARY",
            "plate_id": "",
            "correct_positions": "",
            "response_positions": "",
            "correct_count": "",
            "plate_score": "",
            "HRR_total_score": total_score,
            "HRR_max_score": max_score,
        })

        filename = f"{participant['participant_id']}_HRR.csv"
        export_csv(self.output_dir / filename, rows)
        messagebox.showinfo("Saved", f"Result saved to outputs/{filename}")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Color Vision Tests")
        self.geometry("1400x760")
        self.configure(bg="black")

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        self.output_dir = Path(__file__).resolve().parents[2] / "outputs"

        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        self.participant_id_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.age_var = tk.StringVar()
        self.note_var = tk.StringVar()

        fields = [
            ("Participant ID", self.participant_id_var),
            ("Name", self.name_var),
            ("Age", self.age_var),
            ("Note", self.note_var),
        ]
        for col, (label, var) in enumerate(fields):
            ttk.Label(top, text=label).grid(row=0, column=col * 2, sticky="w", padx=4, pady=4)
            ttk.Entry(top, textvariable=var, width=16).grid(row=0, column=col * 2 + 1, sticky="w", padx=4, pady=4)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        notebook.add(
            ArrangementFrame(notebook, D15Test.create_default, self.get_participant_info, self.output_dir),
            text="D15",
        )
        notebook.add(
            ArrangementFrame(notebook, FMD15Test.create_default, self.get_participant_info, self.output_dir),
            text="FM D-15",
        )
        notebook.add(HRRFrame(notebook, self.get_participant_info, self.output_dir), text="HRR")

    def get_participant_info(self):
        return {
            "participant_id": self.participant_id_var.get().strip(),
            "name": self.name_var.get().strip(),
            "age": self.age_var.get().strip(),
            "note": self.note_var.get().strip(),
        }


def main():
    app = App()
    app.mainloop()