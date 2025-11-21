from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush

class AnnotationCanvas(QWidget):
    # 信号：当用户画完一个框时通知主窗口
    box_created = pyqtSignal(QRectF) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 500)
        self.setStyleSheet("background-color: #202020;")
        self.setMouseTracking(True)
        
        # 状态
        self.pixmap = None
        self.view_scale = 1.0
        self.view_offset = QPointF(0, 0)
        self.annotations_to_draw = [] # [(rect, color, label, is_selected), ...]
        
        # 交互
        self.drawing = False
        self.panning = False
        self.last_mouse_pos = QPointF()
        self.start_pos = QPointF()
        self.current_rect = QRectF()

    def set_image(self, pixmap):
        self.pixmap = pixmap
        self.update()

    def set_annotations(self, annos):
        """接收主窗口传来的待绘制数据"""
        self.annotations_to_draw = annos
        self.update()

    def reset_view(self):
        if not self.pixmap: return
        cw, ch = self.width(), self.height()
        pw, ph = self.pixmap.width(), self.pixmap.height()
        self.view_scale = min(cw/pw, ch/ph) * 0.95
        new_w, new_h = pw * self.view_scale, ph * self.view_scale
        self.view_offset = QPointF((cw - new_w)/2, (ch - new_h)/2)
        self.update()

    # === 坐标变换 ===
    def screen_to_buffer(self, pos):
        return (pos - self.view_offset) / self.view_scale

    # === 事件处理 ===
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        if self.pixmap:
            painter.translate(self.view_offset)
            painter.scale(self.view_scale, self.view_scale)
            painter.drawPixmap(0, 0, self.pixmap)

            # 绘制传入的标注
            # 线宽随缩放反向调整，保持视觉一致
            inv_scale = 1.0 / self.view_scale
            
            for rect, color, label, is_selected in self.annotations_to_draw:
                pen_width = 2.0 * inv_scale if is_selected else 1.5 * inv_scale
                style = Qt.PenStyle.SolidLine if is_selected else Qt.PenStyle.DashLine
                painter.setPen(QPen(color, pen_width, style))
                
                brush = QColor(color)
                brush.setAlpha(40 if is_selected else 0)
                painter.setBrush(QBrush(brush))
                
                painter.drawRect(rect)
                
                # 绘制标签
                painter.save()
                painter.translate(rect.topLeft())
                painter.scale(inv_scale, inv_scale) # 抵消缩放
                
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
                bg = QRectF(0, -22, max(60, len(label)*10), 20)
                painter.fillRect(bg, color)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(bg, Qt.AlignmentFlag.AlignCenter, label)
                painter.restore()

            # 绘制正在画的框
            if self.drawing:
                painter.setPen(QPen(Qt.GlobalColor.white, 1.0 * inv_scale, Qt.PenStyle.DotLine))
                painter.setBrush(QBrush(QColor(255, 255, 255, 30)))
                painter.drawRect(self.current_rect)

    def wheelEvent(self, event):
        if not self.pixmap: return
        factor = 1.2 if event.angleDelta().y() > 0 else 1/1.2
        new_scale = self.view_scale * factor
        if 0.01 < new_scale < 50.0:
            mouse = event.position()
            img_pos = (mouse - self.view_offset) / self.view_scale
            self.view_offset = mouse - img_pos * new_scale
            self.view_scale = new_scale
            self.update()

    def mousePressEvent(self, event):
        if not self.pixmap: return
        if event.button() == Qt.MouseButton.RightButton:
            self.panning = True
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.start_pos = self.screen_to_buffer(event.position())
            self.current_rect = QRectF(self.start_pos, self.start_pos)

    def mouseMoveEvent(self, event):
        if self.panning:
            delta = event.position() - self.last_mouse_pos
            self.view_offset += delta
            self.last_mouse_pos = event.position()
            self.update()
        elif self.drawing:
            curr = self.screen_to_buffer(event.position())
            self.current_rect = QRectF(self.start_pos, curr).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.panning = False
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            img_rect = QRectF(0, 0, self.pixmap.width(), self.pixmap.height())
            final_rect = self.current_rect.intersected(img_rect)
            if final_rect.width() > 1 and final_rect.height() > 1:
                # 发送信号给主窗口处理业务逻辑
                self.box_created.emit(final_rect)
            self.current_rect = QRectF()
            self.update()