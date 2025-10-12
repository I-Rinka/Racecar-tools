import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector

class DataEditor(QWidget):
    """弹出编辑窗口"""
    def __init__(self, df, x_name, y_name, index_list, save_callback):
        super().__init__()
        self.df = df
        self.x_name = x_name
        self.y_name = y_name
        self.index_list = index_list
        self.save_callback = save_callback
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.table = QTableWidget(len(self.index_list), 2)
        self.table.setHorizontalHeaderLabels([self.x_name, self.y_name])

        # ✅ 设置选择行为与编辑方式
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)

        # 填充数据
        for row, idx in enumerate(self.index_list):
            self.table.setItem(row, 0, QTableWidgetItem(str(self.df.loc[idx, self.x_name])))
            self.table.setItem(row, 1, QTableWidgetItem(str(self.df.loc[idx, self.y_name])))

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_and_close)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.setWindowTitle("编辑选中数据")
        self.resize(720, 600)

        # ✅ 注册信号和事件过滤器
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.installEventFilter(self)

    def on_item_changed(self, item):
        """当编辑单元格时，如果存在多选，则进入批量编辑模式"""
        if hasattr(self, "_updating") and self._updating:
            return

        selected = self.table.selectedIndexes()
        if len(selected) > 1:
            # ✅ 批量编辑模式
            new_value = item.text()
            col = item.column()
            self._updating = True
            for index in selected:
                if index.column() == col:
                    self.table.item(index.row(), col).setText(new_value)
                    df_idx = self.index_list[index.row()]
                    col_name = self.x_name if col == 0 else self.y_name
                    self.df.loc[df_idx, col_name] = float(new_value)
            self._updating = False
        else:
            # ✅ 单个编辑
            row, col = item.row(), item.column()
            df_idx = self.index_list[row]
            col_name = self.x_name if col == 0 else self.y_name
            self.df.loc[df_idx, col_name] = float(item.text())

    def eventFilter(self, obj, event):
        """捕获 Delete 键实现删除整行"""
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
                        self.df.drop(df_idx, inplace=True)
                        self.table.removeRow(row)
                        del self.index_list[row]
            return True
        return super().eventFilter(obj, event)

    def save_and_close(self):
        """保存用户修改回原DataFrame"""
        for row, idx in enumerate(self.index_list):
            x_item = self.table.item(row, 0)
            y_item = self.table.item(row, 1)
            if x_item is not None and y_item is not None:
                x_val = float(x_item.text())
                y_val = float(y_item.text())
                self.df.loc[idx, self.x_name] = x_val
                self.df.loc[idx, self.y_name] = y_val

        # 调用回调保存
        self.save_callback(self.df)
        self.close()