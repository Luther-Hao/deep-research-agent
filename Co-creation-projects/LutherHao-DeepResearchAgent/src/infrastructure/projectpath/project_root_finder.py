import os.path


class ProjectRootFinder:
    """项目根目录查找器"""
    DEFAULT_MAKERS = [
        "application.yaml",
        "main.ipynb",
    ]


    @staticmethod
    def find_by_markers(start_path: str = None, makers: list = None) -> str:
        """通过标志文件查找项目根目录"""
        if start_path is None:
            start_path = os.path.dirname(os.path.abspath(__file__))

        if makers is None:
            makers = ProjectRootFinder.DEFAULT_MAKERS

        current_path = os.path.abspath(start_path)

        while True:
            for maker in makers:
                if os.path.exists(os.path.join(current_path, maker)):
                    return current_path

            parent_path = os.path.dirname(current_path)
            if parent_path == current_path:
                # 到达根目录,直接返回
                return os.path.dirname(os.path.abspath(__file__))

            current_path = parent_path



    @classmethod
    def get_project_root(cls) -> str:
        """获取当前工程根目录"""
        return cls.find_by_markers()

if __name__ == '__main__':
    print(ProjectRootFinder.get_project_root())