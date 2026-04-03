"""
Skill 系统 - 解决关卡的技能
"""

import random
import math
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .types import SkillType, GateType


@dataclass
class SkillResult:
    """Skill 执行结果"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    confidence: float = 1.0


class SkillExecutor:
    """Skill 执行器"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.available_skills = {
            SkillType.MATH_COMPUTATION: self.math_computation,
            SkillType.LOGICAL_REASONING: self.logical_reasoning,
            SkillType.CIPHER_DECRYPTION: self.cipher_decryption,
            SkillType.PATTERN_RECOGNITION: self.pattern_recognition,
            SkillType.CODE_EXECUTION: self.code_execution,
            SkillType.WEB_SEARCH: self.web_search,
        }
        self.skill_usage_count = {skill: 0 for skill in SkillType}
    
    def execute(self, skill_type: SkillType, gate_data: Dict[str, Any]) -> SkillResult:
        """执行 skill"""
        if skill_type not in self.available_skills:
            return SkillResult(
                success=False,
                message=f"Unknown skill type: {skill_type}",
                confidence=0.0
            )
        
        executor = self.available_skills[skill_type]
        result = executor(gate_data)
        
        if result.success:
            self.skill_usage_count[skill_type] += 1
        
        return result
    
    def math_computation(self, gate_data: Dict[str, Any]) -> SkillResult:
        """数学计算 skill"""
        question_type = gate_data.get("question_type", "arithmetic")
        
        if question_type == "arithmetic":
            # 算术题
            answer = gate_data.get("answer")
            user_answer = gate_data.get("user_answer")
            
            if answer is None:
                return SkillResult(
                    success=False,
                    message="Missing answer in gate data",
                    confidence=0.0
                )
            
            if user_answer == answer:
                return SkillResult(
                    success=True,
                    message=f"Correct! {gate_data.get('question')} = {answer}",
                    data={"answer": answer}
                )
            else:
                return SkillResult(
                    success=False,
                    message=f"Wrong answer. Expected {answer}, got {user_answer}",
                    confidence=0.8
                )
        
        elif question_type == "algebra":
            # 代数题
            equation = gate_data.get("equation")
            solution = gate_data.get("solution")
            
            return SkillResult(
                success=True,
                message=f"Solved equation: {equation}, x = {solution}",
                data={"solution": solution}
            )
        
        elif question_type == "geometry":
            # 几何题
            shape = gate_data.get("shape")
            calculation = gate_data.get("calculation")
            result = gate_data.get("result")
            
            return SkillResult(
                success=True,
                message=f"Calculated {shape}: {calculation} = {result}",
                data={"result": result}
            )
        
        return SkillResult(
            success=False,
            message=f"Unknown math question type: {question_type}",
            confidence=0.0
        )
    
    def logical_reasoning(self, gate_data: Dict[str, Any]) -> SkillResult:
        """逻辑推理 skill"""
        puzzle_type = gate_data.get("puzzle_type", "deduction")
        
        if puzzle_type == "deduction":
            # 演绎推理
            premises = gate_data.get("premises", [])
            conclusion = gate_data.get("conclusion")
            
            return SkillResult(
                success=True,
                message=f"Logical deduction from {len(premises)} premises: {conclusion}",
                data={"conclusion": conclusion, "premises": premises}
            )
        
        elif puzzle_type == "sequence":
            # 序列推理
            sequence = gate_data.get("sequence", [])
            next_item = gate_data.get("next_item")
            
            return SkillResult(
                success=True,
                message=f"Next item in sequence {sequence}: {next_item}",
                data={"sequence": sequence, "next": next_item}
            )
        
        elif puzzle_type == "truth_table":
            # 真值表
            expression = gate_data.get("expression")
            truth_value = gate_data.get("truth_value")
            
            return SkillResult(
                success=True,
                message=f"Evaluated: {expression} = {truth_value}",
                data={"expression": expression, "value": truth_value}
            )
        
        return SkillResult(
            success=False,
            message=f"Unknown logic puzzle type: {puzzle_type}",
            confidence=0.0
        )
    
    def cipher_decryption(self, gate_data: Dict[str, Any]) -> SkillResult:
        """密码解密 skill"""
        cipher_type = gate_data.get("cipher_type", "caesar")
        encrypted = gate_data.get("encrypted", "")
        
        if cipher_type == "caesar":
            # 凯撒密码
            shift = gate_data.get("shift", 3)
            decrypted = ""
            for char in encrypted:
                if char.isalpha():
                    base = ord('A') if char.isupper() else ord('a')
                    decrypted += chr((ord(char) - base - shift) % 26 + base)
                else:
                    decrypted += char
            
            return SkillResult(
                success=True,
                message=f"Decrypted (Caesar shift={shift}): {encrypted} → {decrypted}",
                data={"decrypted": decrypted, "shift": shift}
            )
        
        elif cipher_type == "substitution":
            # 替换密码
            key = gate_data.get("key", {})
            decrypted = "".join(key.get(c, c) for c in encrypted)
            
            return SkillResult(
                success=True,
                message=f"Decrypted (Substitution): {encrypted} → {decrypted}",
                data={"decrypted": decrypted}
            )
        
        elif cipher_type == "base64":
            # Base64
            import base64
            try:
                decrypted = base64.b64decode(encrypted).decode('utf-8')
                return SkillResult(
                    success=True,
                    message=f"Decrypted (Base64): {encrypted} → {decrypted}",
                    data={"decrypted": decrypted}
                )
            except Exception as e:
                return SkillResult(
                    success=False,
                    message=f"Base64 decode failed: {e}",
                    confidence=0.0
                )
        
        return SkillResult(
            success=False,
            message=f"Unknown cipher type: {cipher_type}",
            confidence=0.0
        )
    
    def pattern_recognition(self, gate_data: Dict[str, Any]) -> SkillResult:
        """模式识别 skill"""
        pattern_type = gate_data.get("pattern_type", "sequence")
        
        if pattern_type == "sequence":
            # 序列模式
            items = gate_data.get("items", [])
            pattern = gate_data.get("pattern", "unknown")
            
            return SkillResult(
                success=True,
                message=f"Recognized pattern '{pattern}' in {items}",
                data={"pattern": pattern, "items": items}
            )
        
        elif pattern_type == "visual":
            # 视觉模式
            grid = gate_data.get("grid", [])
            pattern = gate_data.get("pattern", "unknown")
            
            return SkillResult(
                success=True,
                message=f"Recognized visual pattern: {pattern}",
                data={"grid": grid, "pattern": pattern}
            )
        
        elif pattern_type == "numeric":
            # 数字模式
            numbers = gate_data.get("numbers", [])
            formula = gate_data.get("formula", "unknown")
            
            return SkillResult(
                success=True,
                message=f"Recognized numeric pattern: {formula}",
                data={"numbers": numbers, "formula": formula}
            )
        
        return SkillResult(
            success=False,
            message=f"Unknown pattern type: {pattern_type}",
            confidence=0.0
        )
    
    def code_execution(self, gate_data: Dict[str, Any]) -> SkillResult:
        """代码执行 skill"""
        code = gate_data.get("code", "")
        language = gate_data.get("language", "python")
        
        # 简化版本，实际应该用沙箱执行
        if language == "python":
            try:
                # 这里只是模拟，不实际执行代码
                output = f"Executed {language} code successfully"
                return SkillResult(
                    success=True,
                    message=output,
                    data={"output": output, "language": language}
                )
            except Exception as e:
                return SkillResult(
                    success=False,
                    message=f"Code execution failed: {e}",
                    confidence=0.0
                )
        
        return SkillResult(
            success=False,
            message=f"Unsupported language: {language}",
            confidence=0.0
        )
    
    def web_search(self, gate_data: Dict[str, Any]) -> SkillResult:
        """网络搜索 skill"""
        query = gate_data.get("query", "")
        
        # 模拟搜索结果
        results = [
            f"Result 1 for '{query}'",
            f"Result 2 for '{query}'",
            f"Result 3 for '{query}'",
        ]
        
        return SkillResult(
            success=True,
            message=f"Found {len(results)} results for '{query}'",
            data={"query": query, "results": results}
        )


class GateGenerator:
    """关卡生成器"""
    
    def __init__(self, difficulty: int = 1):
        self.difficulty = difficulty  # 1-5
    
    def generate_gate(self, pos: Tuple[int, int], gate_type: GateType) -> 'Gate':
        """生成关卡"""
        from .types import Gate, SkillType
        
        gate = Gate(
            gate_type=gate_type,
            difficulty=self.difficulty,
        )
        
        if gate_type == GateType.MATH:
            gate.question = self._generate_math_question()
            gate.required_skill = SkillType.MATH_COMPUTATION
            gate.description = f"Solve the math problem at {pos}"
        
        elif gate_type == GateType.LOGIC:
            gate.question = self._generate_logic_puzzle()
            gate.required_skill = SkillType.LOGICAL_REASONING
            gate.description = f"Solve the logic puzzle at {pos}"
        
        elif gate_type == GateType.CIPHER:
            gate.question = self._generate_cipher()
            gate.required_skill = SkillType.CIPHER_DECRYPTION
            gate.description = f"Decrypt the cipher at {pos}"
        
        elif gate_type == GateType.PUZZLE:
            gate.question = self._generate_pattern()
            gate.required_skill = SkillType.PATTERN_RECOGNITION
            gate.description = f"Recognize the pattern at {pos}"
        
        elif gate_type == GateType.COLLABORATION:
            gate.requires_collaboration = True
            gate.collaborating_agents = []  # 需要其他 Agent 帮助
            gate.description = f"Collaborate with other agents at {pos}"
        
        return gate
    
    def _generate_math_question(self) -> Dict[str, Any]:
        """生成数学题"""
        question_types = ["arithmetic", "algebra", "geometry"]
        question_type = random.choice(question_types)
        
        if question_type == "arithmetic":
            a = random.randint(1, 20 * self.difficulty)
            b = random.randint(1, 20 * self.difficulty)
            op = random.choice(["+", "-", "*"])
            
            if op == "+":
                answer = a + b
            elif op == "-":
                answer = a - b
            else:
                answer = a * b
            
            return {
                "question_type": "arithmetic",
                "question": f"{a} {op} {b}",
                "answer": answer,
            }
        
        elif question_type == "algebra":
            x = random.randint(1, 10)
            a = random.randint(2, 5)
            b = random.randint(1, 10)
            result = a * x + b
            
            return {
                "question_type": "algebra",
                "equation": f"{a}x + {b} = {result}",
                "solution": x,
            }
        
        else:  # geometry
            side = random.randint(1, 10)
            area = side * side
            
            return {
                "question_type": "geometry",
                "shape": "square",
                "calculation": f"area of square with side {side}",
                "result": area,
            }
    
    def _generate_logic_puzzle(self) -> Dict[str, Any]:
        """生成逻辑题"""
        puzzle_types = ["deduction", "sequence", "truth_table"]
        puzzle_type = random.choice(puzzle_types)
        
        if puzzle_type == "sequence":
            start = random.randint(1, 10)
            step = random.randint(1, 5)
            sequence = [start + i * step for i in range(4)]
            next_item = start + 4 * step
            
            return {
                "puzzle_type": "sequence",
                "sequence": sequence,
                "next_item": next_item,
            }
        
        elif puzzle_type == "deduction":
            premises = [
                "All A are B",
                "All B are C",
            ]
            conclusion = "All A are C"
            
            return {
                "puzzle_type": "deduction",
                "premises": premises,
                "conclusion": conclusion,
            }
        
        else:  # truth_table
            return {
                "puzzle_type": "truth_table",
                "expression": "A AND (B OR C)",
                "truth_value": True,
            }
    
    def _generate_cipher(self) -> Dict[str, Any]:
        """生成密码题"""
        cipher_types = ["caesar", "substitution", "base64"]
        cipher_type = random.choice(cipher_types)
        
        words = ["HELLO", "WORLD", "PUZZLE", "SECRET", "CODE"]
        word = random.choice(words)
        
        if cipher_type == "caesar":
            shift = random.randint(1, 25)
            encrypted = ""
            for char in word:
                if char.isalpha():
                    encrypted += chr((ord(char) - ord('A') + shift) % 26 + ord('A'))
                else:
                    encrypted += char
            
            return {
                "cipher_type": "caesar",
                "encrypted": encrypted,
                "shift": shift,
                "answer": word,
            }
        
        elif cipher_type == "substitution":
            import string
            alphabet = string.ascii_uppercase
            shuffled = ''.join(random.sample(alphabet, len(alphabet)))
            key = {s: a for s, a in zip(shuffled, alphabet)}
            
            encrypted = "".join(key.get(c, c) for c in word)
            
            return {
                "cipher_type": "substitution",
                "encrypted": encrypted,
                "key": key,
                "answer": word,
            }
        
        else:  # base64
            import base64
            encrypted = base64.b64encode(word.encode()).decode()
            
            return {
                "cipher_type": "base64",
                "encrypted": encrypted,
                "answer": word,
            }
    
    def _generate_pattern(self) -> Dict[str, Any]:
        """生成模式题"""
        pattern_types = ["sequence", "numeric", "visual"]
        pattern_type = random.choice(pattern_types)
        
        if pattern_type == "sequence":
            start = random.randint(1, 5)
            mult = random.randint(2, 3)
            items = [start * (mult ** i) for i in range(4)]
            
            return {
                "pattern_type": "sequence",
                "items": items,
                "pattern": f"multiply by {mult}",
            }
        
        elif pattern_type == "numeric":
            return {
                "pattern_type": "numeric",
                "numbers": [2, 4, 8, 16],
                "formula": "2^n",
            }
        
        else:  # visual
            return {
                "pattern_type": "visual",
                "grid": [[1, 0, 1], [0, 1, 0], [1, 0, 1]],
                "pattern": "diagonal",
            }
