"""Clueat connector - Shows how food/allergen intelligence plugs into PARM."""

from datetime import timedelta
from typing import Any, Optional

from parm_agents import BaseAgent, AgentCapability, CapabilityType
from parm_context import ContextProvider, ContextResolver
from parm_core import ContextFrame, Result, ParmEngine, CapabilityType as CapType
from parm_workflows import WorkflowBuilder, WorkflowExecutor
from datetime import datetime, timezone


class IngredientAnalysisAgent(BaseAgent):
    """
    Clueat agent: Analyzes ingredients for allergens and nutritional content.
    """

    def __init__(self) -> None:
        super().__init__("ingredient_analyzer", "Analyzes ingredients for safety")

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                type=CapabilityType.ANALYSIS,
                name="allergen_detection",
                description="Detect allergens in ingredients",
                input_schema={
                    "ingredients": "list[string]",
                    "dish_name": "string",
                },
                output_schema={
                    "allergens": "list[string]",
                    "risk_level": "string",
                },
                required_context=["temporal"],
                tags=["food", "allergen", "safety"],
            )
        ]

    def execute(
        self,
        context: Optional[ContextFrame] = None,
        **kwargs: Any
    ) -> Result[Any]:
        """Execute ingredient analysis."""
        ingredients = kwargs.get("ingredients", [])
        dish_name = kwargs.get("dish_name", "Unknown")

        if not ingredients:
            return Result.failure("No ingredients provided")

        # Simulate allergen detection
        allergen_list = []
        common_allergens = {
            "peanut": "peanuts",
            "tree nut": "treenuts",
            "milk": "dairy",
            "egg": "eggs",
            "shellfish": "shellfish",
            "soy": "soy",
            "wheat": "gluten",
        }

        for ingredient in ingredients:
            ingredient_lower = ingredient.lower()
            for allergen_key, allergen_name in common_allergens.items():
                if allergen_key in ingredient_lower:
                    allergen_list.append(allergen_name)

        risk_level = "high" if len(allergen_list) > 2 else "medium" if allergen_list else "low"

        return Result.success({
            "dish_name": dish_name,
            "ingredients_analyzed": len(ingredients),
            "allergens": allergen_list,
            "risk_level": risk_level,
            "safe_for_common_allergies": len(allergen_list) == 0,
        })


class AllergenScoringAgent(BaseAgent):
    """Clueat agent: Scores allergen risk for dishes."""

    def __init__(self) -> None:
        super().__init__("allergen_scorer", "Scores allergen risk")

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                type=CapabilityType.DECISION,
                name="allergen_scoring",
                description="Score allergen risk levels",
                tags=["food", "allergen", "scoring"],
            )
        ]

    def execute(
        self,
        context: Optional[ContextFrame] = None,
        **kwargs: Any
    ) -> Result[Any]:
        """Execute allergen scoring."""
        allergens = kwargs.get("allergens", [])
        risk_level = kwargs.get("risk_level", "low")

        # Score based on allergens
        score = 0
        if risk_level == "high":
            score = 9
        elif risk_level == "medium":
            score = 5
        else:
            score = 1

        recommendation = "Do not serve" if score > 7 else "Warn customer" if score > 3 else "Safe to serve"

        return Result.success({
            "allergen_count": len(allergens),
            "risk_score": score,
            "recommendation": recommendation,
        })


class FoodContextProvider(ContextProvider):
    """Provides food/dietary context."""

    def __init__(self) -> None:
        super().__init__("food_context_provider")
        self._dietary_preferences = {}
        self._allergen_profiles = {}

    def register_user_allergies(self, user_id: str, allergies: list[str]) -> None:
        """Register user allergen profile."""
        self._allergen_profiles[user_id] = allergies

    def get_context(self, entity_id: str, entity_type: str) -> Optional[ContextFrame]:
        """Get food context for a user."""
        if entity_type != "user":
            return None

        allergies = self._allergen_profiles.get(entity_id, [])

        return ContextFrame(
            entity_id=entity_id,
            entity_type=entity_type,
            timestamp=datetime.now(timezone.utc),
            temporal_info={},
            spatial_info={},
            relational_info={},
            domain_data={
                "allergies": allergies,
                "dietary_restrictions": [],
                "preferences": [],
            },
            source="food_context_provider",
            ttl=timedelta(days=1),
        )


def setup_clueat_on_parm(engine: ParmEngine) -> None:
    """
    Set up Clueat on the PARM platform.

    Args:
        engine: ParmEngine instance
    """
    # 1. Register agents
    analyzer_agent = IngredientAnalysisAgent()
    scorer_agent = AllergenScoringAgent()

    engine.register_agent(
        "clueat_analyzer",
        analyzer_agent,
        description="Analyzes food ingredients",
        tags=["food", "clueat"],
        capabilities=["allergen_detection"],
    )

    engine.register_agent(
        "clueat_scorer",
        scorer_agent,
        description="Scores allergen risk",
        tags=["food", "clueat"],
        capabilities=["allergen_scoring"],
    )

    # 2. Register food context provider
    food_provider = FoodContextProvider()
    engine.register_context_provider(
        "clueat_food_provider",
        food_provider,
        description="Provides food and allergen context",
        tags=["food", "allergen"],
    )

    # 3. Create allergen detection workflow
    allergen_workflow = (
        WorkflowBuilder("allergen_workflow", "Detect allergens and assess risk")
        .add_step(
            "scan_ingredients",
            "scan_ingredients",
            inputs={"dish_id": "$dish_id"},
            timeout=timedelta(seconds=10),
        )
        .add_step(
            "parse_ingredients",
            "parse_ingredients",
            depends_on=["scan_ingredients"],
            timeout=timedelta(seconds=5),
        )
        .add_step(
            "detect_allergens",
            "detect_allergens",
            depends_on=["parse_ingredients"],
            timeout=timedelta(seconds=15),
        )
        .add_step(
            "score_risk",
            "score_risk",
            depends_on=["detect_allergens"],
            timeout=timedelta(seconds=5),
        )
        .add_step(
            "notify_if_needed",
            "notify_customer",
            depends_on=["score_risk"],
            condition="score_risk_output['risk_score'] > 3",
            timeout=timedelta(seconds=10),
        )
        .build()
    )

    engine.register_workflow(
        "clueat_allergen_workflow",
        allergen_workflow,
        description="Allergen detection and notification",
        tags=["food", "clueat"],
    )

    # 4. Register workflow handlers
    executor = WorkflowExecutor()

    executor.register_step_handler("scan_ingredients", lambda inputs: scan_ingredients(inputs))
    executor.register_step_handler("parse_ingredients", lambda inputs: parse_ingredients(inputs))
    executor.register_step_handler("detect_allergens", lambda inputs: detect_allergens(inputs))
    executor.register_step_handler("score_risk", lambda inputs: score_risk(inputs))
    executor.register_step_handler("notify_customer", lambda inputs: notify_customer(inputs))

    print("[Clueat] Connected to PARM")
    print("  - Agents: IngredientAnalyzer, AllergenScorer")
    print("  - Workflow: Allergen (scan → parse → detect → score → notify)")
    print("  - Context: FoodContextProvider")


# Handler functions for workflow steps
def scan_ingredients(inputs: dict[str, Any]) -> Result[Any]:
    """Scan ingredients from a dish."""
    dish_id = inputs.get("dish_id")
    return Result.success({
        "dish_id": dish_id,
        "ingredients": ["peanut oil", "egg", "wheat flour", "milk"],
    })


def parse_ingredients(inputs: dict[str, Any]) -> Result[Any]:
    """Parse ingredient list."""
    ingredients = inputs.get("ingredients", [])
    return Result.success({"parsed_ingredients": ingredients})


def detect_allergens(inputs: dict[str, Any]) -> Result[Any]:
    """Detect allergens in parsed ingredients."""
    parsed = inputs.get("parsed_ingredients", [])
    allergens = [ing for ing in parsed if any(a in ing.lower() for a in ["peanut", "egg", "milk"])]
    return Result.success({"allergens": allergens})


def score_risk(inputs: dict[str, Any]) -> Result[Any]:
    """Score the allergen risk."""
    allergens = inputs.get("allergens", [])
    risk_score = min(10, len(allergens) * 3)
    return Result.success({"risk_score": risk_score})


def notify_customer(inputs: dict[str, Any]) -> Result[Any]:
    """Notify customer of allergen risk."""
    return Result.success({"notification_sent": True})
