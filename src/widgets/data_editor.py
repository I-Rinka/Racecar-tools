from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QAbstractItemView,
    QTableWidgetItem, QPushButton, QLineEdit, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal


class DataEditor(QWidget):
    cellHovered = pyqtSignal(str)  # hover 值回传信号

    def __init__(self, df, x_name, y_name, index_list, save_callback):
        super().__init__()
        self.df = df
        self.x_name = x_name
        self.y_name = y_name
        self.index_list = index_list
        self.save_callback = save_callback

        # 状态变量
        self._updating = False
        self._last_edited_value = None        # 字符串形式的上次修改值（用于填充）
        self._last_find_pos = (-1, -1)        # 上次查找到的 (row, col)，用于“查找下一个”
        self._last_find_pos2 = -1
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 顶部：查找栏 + 上次修改显示 + 填充按钮
        top_layout = QHBoxLayout()

        # 查找部分
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入要查找的内容...")
        self.search_btn = QPushButton("查找下一个")
        self.search_btn.clicked.connect(self.find_value)
        self.search_btn2 = QPushButton("查找突出值")
        self.search_btn2.clicked.connect(self.find_outstanding)
        top_layout.addWidget(QLabel("查找："))
        top_layout.addWidget(self.search_input)
        top_layout.addWidget(self.search_btn)
        top_layout.addWidget(self.search_btn2)

        # 显示上次修改值（用于填充）
        self.last_val_label = QLabel("上次修改值：<无>")
        top_layout.addWidget(self.last_val_label)

        # 填充按钮（把多选单元格填成上次修改值）
        self.fill_btn = QPushButton("填充选中")
        self.fill_btn.clicked.connect(self.fill_selected_with_last)
        top_layout.addWidget(self.fill_btn)

        layout.addLayout(top_layout)

        # 表格初始化
        self.table = QTableWidget(len(self.index_list), 2)
        self.table.setHorizontalHeaderLabels([self.x_name, self.y_name])
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)

        for row, idx in enumerate(self.index_list):
            self.table.setItem(row, 0, QTableWidgetItem(str(self.df.loc[idx, self.x_name])))
            self.table.setItem(row, 1, QTableWidgetItem(str(self.df.loc[idx, self.y_name])))

        layout.addWidget(self.table)

        # 保存按钮
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_and_close)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.setWindowTitle("编辑选中数据")
        self.resize(720, 600)

        # 信号与事件
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.installEventFilter(self)
        # 当鼠标在表格的单元格上移动时触发（需要 setMouseTracking = True 在父级或表格中通常已经启用）
        # self.table.cellEntered.connect(self.on_cell_hovered)
        self.table.cellClicked.connect(self.on_cell_hovered)
        self.func = None

    # -------------------
    # Hover：回传值
    # -------------------
    def register_hover_back_index(self, func):
        self.func = func
        
    def on_cell_hovered(self, row, col):
        if self.func is not None:
            self.func(self.index_list[row])

    # -------------------
    # 单元格内容变化：更新 DataFrame，并记录上次修改值（用于填充）
    # -------------------
    def on_item_changed(self, item):
        if self._updating:
            return

        # 先把值更新到 DataFrame（单个）
        row, col = item.row(), item.column()
        df_idx = self.index_list[row]
        col_name = self.x_name if col == 0 else self.y_name

        text_val = item.text().strip()
        # 尝试转换为 float，如果失败保留原文本（避免因非数字抛异常）
        try:
            numeric = float(text_val)
            self.df.loc[df_idx, col_name] = numeric
        except Exception:
            # 非数字：直接保存原字符串（根据需要可调整为忽略/提示）
            self.df.loc[df_idx, col_name] = text_val

        # 记录“上次修改值”（文本形式），更新显示
        self._last_edited_value = text_val
        self.last_val_label.setText(f"上次修改值：{self._last_edited_value}")

        # 若用户多选并修改了一个单元格，自动把该值批量写入（你之前已有的批量逻辑保留）
        # 这里我们继续保留：如果存在多选，并且多选中有同列项，则把它们也设为相同值
        selected = self.table.selectedIndexes()
        if len(selected) > 1:
            col0 = col
            self._updating = True
            for index in selected:
                if index.column() == col0:
                    target_item = self.table.item(index.row(), col0)
                    if target_item is None:
                        target_item = QTableWidgetItem(text_val)
                        self.table.setItem(index.row(), col0, target_item)
                    else:
                        target_item.setText(text_val)
                    # 更新 DataFrame 对应项
                    df_idx2 = self.index_list[index.row()]
                    col_name2 = self.x_name if col0 == 0 else self.y_name
                    try:
                        self.df.loc[df_idx2, col_name2] = float(text_val)
                    except Exception:
                        self.df.loc[df_idx2, col_name2] = text_val
            self._updating = False

    # -------------------
    # 填充按钮：把选中所有单元格填为上次修改值
    # -------------------
    def fill_selected_with_last(self):
        if self._last_edited_value is None:
            QMessageBox.information(self, "提示", "没有可用于填充的“上次修改值”。请先编辑一个单元格以产生该值。")
            return

        selected = self.table.selectedIndexes()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要填充的单元格。")
            return

        # 统一填充值（文本），并更新 DataFrame
        self._updating = True
        for idx in selected:
            r, c = idx.row(), idx.column()
            item = self.table.item(r, c)
            if item is None:
                item = QTableWidgetItem(self._last_edited_value)
                self.table.setItem(r, c, item)
            else:
                item.setText(self._last_edited_value)
            df_idx = self.index_list[r]
            col_name = self.x_name if c == 0 else self.y_name
            try:
                self.df.loc[df_idx, col_name] = float(self._last_edited_value)
            except Exception:
                self.df.loc[df_idx, col_name] = self._last_edited_value
        self._updating = False

    # -------------------
    # 查找（循环查找下一个）
    # -------------------
    def find_value(self):
        text = self.search_input.text()
        if text is None:
            text = ""
        text = text.strip()
        if text == "":
            return

        rows = self.table.rowCount()
        cols = self.table.columnCount()
        total = rows * cols
        if total == 0:
            QMessageBox.information(self, "查找结果", "表格为空。")
            return

        # 计算从哪里开始查找：上一次找到的位置的下一格
        start_index = 0
        last_r, last_c = self._last_find_pos
        if 0 <= last_r < rows and 0 <= last_c < cols:
            start_index = (last_r * cols + last_c + 1) % total

        found = False
        # 线性扫描 total 次以实现循环
        for step in range(total):
            linear = (start_index + step) % total
            r = linear // cols
            c = linear % cols
            item = self.table.item(r, c)
            if item and text == item.text():
                # 找到，选中并滚动到该项
                self.table.setCurrentCell(r, c)
                self.table.scrollToItem(item)
                # 记录位置，供下一次继续查找
                self._last_find_pos = (r, c)
                found = True
                break

        if not found:
            QMessageBox.information(self, "查找结果", f"未找到包含“{text}”的单元格。")
            # 将查找位置重置，下一次从头开始
            self._last_find_pos = (-1, -1)
    
    # -------------------
    # 查找突出值（一看就不正常的速度）
    # -------------------
    def find_outstanding(self):
        rows = self.table.rowCount()
        col = self.table.columnCount() - 1
        if col < 0:
            QMessageBox.information(self, "查找结果", "表格为空。")
            return

        # 计算从哪里开始查找：上一次找到的位置的下一格
        start_index = 0
        if 0 <= self._last_find_pos2 < rows:
            start_index = self._last_find_pos2

        found = False
        # 线性扫描 total 次以实现循环
        for step in range(start_index, rows):
            item = self.table.item(step, col)
            number_str = item.text()
            
            try:
                number = float(number_str)
                if number > 40.0 and number < 1000.0:
                    continue
            except Exception as e:
                pass
            
            self.table.setCurrentCell(step, col)
            self.table.scrollToItem(item)
            self._last_find_pos2 = step
            found = True
            break
            
        if not found:
            QMessageBox.information(self, "查找结果", f"未找到单元格。")
            # 将查找位置重置，下一次从头开始
            self._last_find_pos2 = -1
    
    # -------------------
    # 删除键事件处理：保持原来的删除行功能
    # -------------------
    def eventFilter(self, obj, event):
        if obj == self.table and event.type() == event.KeyPress and event.key() == Qt.Key_Delete:
            selected_rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
            if selected_rows:
                reply = QMessageBox.question(
                    self, "确认删除",
                    f"确定要删除选中的 {len(selected_rows)} 行吗？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    for row in reversed(selected_rows):
                        df_idx = self.index_list[row]
                        # 从 DataFrame 删除
                        try:
                            self.df.drop(df_idx, inplace=True)
                        except Exception:
                            pass
                        # 从表格与索引列表删除
                        self.table.removeRow(row)
                        del self.index_list[row]
            return True
        return super().eventFilter(obj, event)

    # -------------------
    # 保存并关闭
    # -------------------
    def save_and_close(self):
        for row, idx in enumerate(self.index_list):
            x_item = self.table.item(row, 0)
            y_item = self.table.item(row, 1)
            if x_item is not None and y_item is not None:
                x_text = x_item.text().strip()
                y_text = y_item.text().strip()
                try:
                    x_val = float(x_text)
                except Exception:
                    x_val = x_text
                try:
                    y_val = float(y_text)
                except Exception:
                    y_val = y_text
                self.df.loc[idx, self.x_name] = x_val
                self.df.loc[idx, self.y_name] = y_val

        # 调用回调保存
        self.save_callback(self.df)
        self.close()
