class Ingredient:
    def __init__(self, name, amount, amount_type):
        self.name = name
        self.amount = amount
        self.amount_type = amount_type

class Recipe:
    def __init__(self, name, prep_time, calories, ingredients, steps):
        self.name = name
        self.prep_time = prep_time 
        self.calories = calories
        self.ingredients = ingredients 
        self.steps = steps

days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
meal_times = ["Breakfast", "Dinner"]

# Sample 14 recipes
sample_recipes = [
    # 1
    Recipe(
        "Greek Yogurt Parfait",
        "10 min",
        320,
        [
            Ingredient("Greek Yogurt", 200, "g"),
            Ingredient("Granola", 30, "g"),
            Ingredient("Mixed Berries", 80, "g"),
            Ingredient("Honey", 10, "g"),
        ],
        [
            "Spoon the Greek yogurt into a bowl or glass.",
            "Layer granola and mixed berries on top.",
            "Drizzle with honey and serve immediately."
        ]
    ),

    # 2
    Recipe(
        "Baked Salmon with Quinoa",
        "30 min",
        520,
        [
            Ingredient("Salmon Fillet", 180, "g"),
            Ingredient("Quinoa (dry)", 70, "g"),
            Ingredient("Broccoli Florets", 120, "g"),
            Ingredient("Olive Oil", 10, "g"),
            Ingredient("Lemon Juice", 10, "g"),
        ],
        [
            "Season the salmon with salt, pepper, and a drizzle of olive oil, then bake at 180°C for 15–18 minutes.",
            "Cook quinoa according to package instructions.",
            "Steam broccoli until tender and serve with salmon and quinoa, finishing with lemon juice."
        ]
    ),

    # 3
    Recipe(
        "Veggie Omelette",
        "15 min",
        310,
        [
            Ingredient("Egg", 2, "unit"),
            Ingredient("Egg White", 60, "g"),
            Ingredient("Spinach", 40, "g"),
            Ingredient("Cherry Tomato", 50, "g"),
            Ingredient("Feta Cheese", 20, "g"),
        ],
        [
            "Whisk eggs and egg whites with a pinch of salt and pepper.",
            "Sauté spinach and halved cherry tomatoes in a non-stick pan, then pour the eggs over.",
            "Sprinkle with feta and cook until set, folding in half before serving."
        ]
    ),

    # 4
    Recipe(
        "Turkey Stir-Fry with Brown Rice",
        "25 min",
        540,
        [
            Ingredient("Turkey Breast Strips", 160, "g"),
            Ingredient("Brown Rice (dry)", 70, "g"),
            Ingredient("Bell Pepper", 60, "g"),
            Ingredient("Carrot", 50, "g"),
            Ingredient("Soy Sauce", 10, "g"),
            Ingredient("Olive Oil", 8, "g"),
        ],
        [
            "Cook brown rice according to package instructions.",
            "Stir-fry turkey strips in olive oil until browned, then add sliced bell pepper and carrot.",
            "Add soy sauce and cook until vegetables are tender, then serve over brown rice."
        ]
    ),

    # 5
    Recipe(
        "Overnight Oats with Apple",
        "5 min + overnight",
        290,
        [
            Ingredient("Rolled Oats", 50, "g"),
            Ingredient("Milk or Plant Milk", 150, "ml"),
            Ingredient("Apple", 80, "g"),
            Ingredient("Chia Seeds", 10, "g"),
            Ingredient("Cinnamon", 2, "g"),
        ],
        [
            "Combine oats, milk, chia seeds, and cinnamon in a jar and stir well.",
            "Refrigerate overnight.",
            "In the morning, top with chopped apple and serve."
        ]
    ),

    # 6
    Recipe(
        "Lentil and Veggie Bowl",
        "30 min",
        480,
        [
            Ingredient("Cooked Lentils", 150, "g"),
            Ingredient("Sweet Potato", 120, "g"),
            Ingredient("Spinach", 40, "g"),
            Ingredient("Cherry Tomato", 60, "g"),
            Ingredient("Olive Oil", 10, "g"),
            Ingredient("Balsamic Vinegar", 10, "g"),
        ],
        [
            "Roast cubed sweet potato with a little olive oil and salt at 200°C for 20 minutes.",
            "Warm the lentils in a pan and add spinach and halved cherry tomatoes.",
            "Serve lentils and vegetables in a bowl with roasted sweet potato and drizzle with balsamic vinegar."
        ]
    ),

    # 7
    Recipe(
        "Avocado Toast with Egg",
        "12 min",
        340,
        [
            Ingredient("Wholegrain Bread Slice", 2, "unit"),
            Ingredient("Avocado", 70, "g"),
            Ingredient("Egg", 1, "unit"),
            Ingredient("Cherry Tomato", 40, "g"),
            Ingredient("Lemon Juice", 5, "g"),
        ],
        [
            "Toast the bread slices until crisp.",
            "Mash the avocado with lemon juice, salt, and pepper, then spread over the toast.",
            "Top with a fried or poached egg and sliced cherry tomatoes."
        ]
    ),

    # 8
    Recipe(
        "Tofu and Vegetable Curry",
        "30 min",
        510,
        [
            Ingredient("Firm Tofu", 150, "g"),
            Ingredient("Coconut Milk (light)", 150, "ml"),
            Ingredient("Mixed Vegetables (e.g., bell pepper, zucchini, carrot)", 150, "g"),
            Ingredient("Curry Paste", 15, "g"),
            Ingredient("Brown Rice (dry)", 60, "g"),
        ],
        [
            "Cook brown rice according to package instructions.",
            "Sauté cubed tofu and chopped vegetables in a pan until lightly browned.",
            "Stir in curry paste and coconut milk and simmer until vegetables are tender, then serve over rice."
        ]
    ),

    # 9
    Recipe(
        "Berry Smoothie Bowl",
        "8 min",
        300,
        [
            Ingredient("Frozen Berries", 120, "g"),
            Ingredient("Banana", 70, "g"),
            Ingredient("Greek Yogurt", 120, "g"),
            Ingredient("Milk or Plant Milk", 80, "ml"),
            Ingredient("Granola", 20, "g"),
        ],
        [
            "Blend frozen berries, banana, yogurt, and milk until thick and smooth.",
            "Pour into a bowl.",
            "Top with granola and extra berries if desired."
        ]
    ),

    # 10
    Recipe(
        "Baked Cod with Vegetables",
        "28 min",
        430,
        [
            Ingredient("Cod Fillet", 170, "g"),
            Ingredient("Cherry Tomato", 80, "g"),
            Ingredient("Zucchini", 80, "g"),
            Ingredient("Olive Oil", 10, "g"),
            Ingredient("Lemon", 40, "g"),
        ],
        [
            "Place cod on a baking tray and surround with sliced zucchini and cherry tomatoes.",
            "Drizzle with olive oil, season with salt and pepper, and bake at 190°C for 18–20 minutes.",
            "Serve with lemon wedges."
        ]
    ),

    # 11
    Recipe(
        "Cottage Cheese & Fruit Bowl",
        "7 min",
        280,
        [
            Ingredient("Cottage Cheese", 150, "g"),
            Ingredient("Pear", 80, "g"),
            Ingredient("Walnuts", 15, "g"),
            Ingredient("Honey", 8, "g"),
            Ingredient("Cinnamon", 2, "g"),
        ],
        [
            "Place cottage cheese in a bowl.",
            "Top with sliced pear and chopped walnuts.",
            "Finish with honey and a sprinkle of cinnamon."
        ]
    ),

    # 12
    Recipe(
        "Wholegrain Pasta with Tomato & Spinach",
        "25 min",
        520,
        [
            Ingredient("Wholegrain Pasta (dry)", 70, "g"),
            Ingredient("Tomato Passata", 120, "g"),
            Ingredient("Spinach", 50, "g"),
            Ingredient("Olive Oil", 8, "g"),
            Ingredient("Parmesan Cheese", 15, "g"),
        ],
        [
            "Cook wholegrain pasta according to package instructions.",
            "Warm tomato passata in a pan with olive oil and wilt the spinach in the sauce.",
            "Toss cooked pasta in the sauce and serve with grated Parmesan."
        ]
    ),

    # 13
    Recipe(
        "Chia Pudding with Mango",
        "5 min + chilling",
        260,
        [
            Ingredient("Chia Seeds", 25, "g"),
            Ingredient("Milk or Plant Milk", 200, "ml"),
            Ingredient("Mango", 80, "g"),
            Ingredient("Vanilla Extract", 2, "g"),
        ],
        [
            "Mix chia seeds with milk and vanilla extract in a jar and stir well.",
            "Refrigerate for at least 2 hours or overnight, stirring once after 15 minutes.",
            "Top with diced mango before serving."
        ]
    ),

    # 14
    Recipe(
        "Stuffed Bell Peppers with Turkey",
        "35 min",
        500,
        [
            Ingredient("Bell Pepper", 2, "unit"),
            Ingredient("Ground Turkey", 150, "g"),
            Ingredient("Cooked Brown Rice", 70, "g"),
            Ingredient("Tomato Sauce", 80, "g"),
            Ingredient("Onion", 40, "g"),
        ],
        [
            "Cut the tops off the bell peppers and remove the seeds.",
            "Sauté chopped onion and ground turkey until cooked, then mix with cooked rice and tomato sauce.",
            "Stuff the peppers with the mixture and bake at 190°C for 20–25 minutes."
        ]
    ),
]

