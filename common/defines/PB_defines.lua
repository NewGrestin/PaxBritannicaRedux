-- Game
NDefines.NGame.START_DATE = "1933.1.1.12"
NDefines.NGame.END_DATE = "2000.1.1.1"
NDefines.NGame.HANDS_OFF_START_TAG = "ADR"                                  -- Andorra is and will not be involved in anything yet
NDefines.NCountry.BASE_MAX_COMMAND_POWER = 120.0                            -- Vanilla is 80.0
-- Focus
NDefines.NFocus.FOCUS_POINT_DAYS = 1                                        -- Vanilla is 7
-- Diplomacy
NDefines.NDiplomacy.MAX_TRUST_VALUE = 200									-- Vanilla is 100
NDefines.NDiplomacy.MIN_TRUST_VALUE = -200									-- Vanilla is -100
NDefines.NDiplomacy.MAX_OPINION_VALUE = 200									-- Vanilla is 100
NDefines.NDiplomacy.MIN_OPINION_VALUE = -200								-- Vanilla is -100
NDefines.NDiplomacy.BASE_TRUCE_PERIOD = 400									-- Vanilla is 180
NDefines.NDiplomacy.VERY_GOOD_OPINION = 100									-- Vanilla is 50
NDefines.NDiplomacy.VERY_BAD_OPINION = -100									-- Vanilla is -50
NDefines.NDiplomacy.FRONT_IS_DANGEROUS = 0									-- Vanilla is -100
NDefines.NDiplomacy.TENSION_TIME_SCALE_START_DATE = "1933.1.1.12"
NDefines.NAI.DIPLOMACY_ACCEPT_CONDITIONAL_SURRENDER_GLOBAL_TENSION = -1000	-- Vanilla is -10. Adds -10 to conditional surrender acceptance per 1 WT point - disables conditional surrender for AI
-- Country
NDefines.NCountry.MIN_STABILITY = -1.0                                      -- Vanilla is 0.0
-- Peace Conferences
NDefines.NDiplomacy.PEACE_SCORE_SCALE_FACTOR = 2.00							-- Vanilla is 1.35
NDefines.NDiplomacy.PEACE_SCORE_DISTRIBUTION = { 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2 } -- Vanilla is 0.2 in the first five turns
NDefines.NDiplomacy.PEACE_CONTEST_REFUND_FACTOR = { 1.0, 0.8, 0.5, 0.2 } 	-- Vanilla is 1.0, 0.92, 0.84, 0.76
NDefines.NAI.PEACE_AI_EVALUATE_FOR_NON_ALLIES = true						-- Vanilla is false
NDefines.NAI.PEACE_AI_EVALUATE_OTHER_ALWAYS = true							-- Vanilla is false
NDefines.NDiplomacy.PEACE_ACTION_MAX_COST = 99999							-- Vanilla is 9999
-- Military
NDefines.NMilitary.MAX_DIVISION_SUPPORT_WIDTH = 2							-- Vanilla is 1
NDefines.NMilitary.MAX_DIVISION_SUPPORT_HEIGHT = 4							-- Vanilla is 5
NDefines.NMilitary.MAX_ARMY_EXPERIENCE = 750                                -- Vanilla is 500
NDefines.NMilitary.MAX_NAVY_EXPERIENCE = 750                                -- Vanilla is 500
NDefines.NMilitary.MAX_AIR_EXPERIENCE = 750                                 -- Vanilla is 500
NDefines.NMilitary.SLOWEST_SPEED = 2 -- yes i had to change this            -- Vanilla is 4
-- Volunteers
NDefines.NAI.SEND_VOLUNTEER_EVAL_BASE_DISTANCE = 1000.0  					-- Vanilla is 175.0
-- General AI
NDefines.NAI.MIN_AI_SCORE_TO_TRADE_LAW_OVERRIDE_HARD_CODED_SCORE = 0.0		-- Vanilla is 1000.0
NDefines.NAI.XP_RATIO_REQUIRED_TO_RESEARCH_WITH_XP = 1.5					-- Vanilla is 2 - needed to make AI research naval techs with XP
NDefines.NAI.RESEARCH_WITH_XP_AI_WEIGHT_MULT = 3.0							-- Vanilla is 1.2 - bigger prio for naval techs if can spend XP

NDefines.NAI.ASSIGN_TANKS_TO_NON_WAR_FRONT = 0								-- Vanilla is 0.4
NDefines.NAI.ASSIGN_TANKS_TO_MOUNTAINS = -12								-- Vanilla is -6
NDefines.NAI.ASSIGN_TANKS_TO_JUNGLE = -12									-- Vanilla is -6

NDefines.NAI.FRONT_EVAL_UNIT_ACCURACY = 1.5								-- Vanilla is 1.0
NDefines.NAI.MIN_FORCE_RATIO_TO_PROTECT = 0									-- Vanilla is 0.5
NDefines.NAI.FRONT_EVAL_PERCENT_TO_ASSIST_ALLY_FRONT = 0					-- Vanilla is 0.5
NDefines.NAI.MIN_FACTORIES_TO_WANT_TO_IMPORT = {  -- minimum number of civilian factories the AI must have to consider importing a resource - per strategic resource. Default 0, array -should- be updated with new resources, or if the order changes.
		0, -- oil
		0, -- aluminium
		0, -- rubber
		0, -- tungsten
		0, -- steel
		0, -- chromium
        0, -- grain
		10, -- coal
	}
-- Combat AI
NDefines.NAI.FORTIFIED_RATIO_TO_CONSIDER_A_FRONT_FORTIFIED = 0.4			-- Vanilla is 0.5
NDefines.NAI.HEAVILY_FORTIFIED_RATIO_TO_CONSIDER_A_FRONT_FORTIFIED = 0.6	-- Vanilla is 0.5
NDefines.NMilitary.PLAN_EXECUTE_CAREFUL_MAX_FORT = 3						-- Vanilla is 5
NDefines.NAI.ATTACK_HEAVILY_DEFENDED_LIMIT = 1.0							-- Vanilla is 0.5
NDefines.NAI.LAND_COMBAT_OUR_COMBATS_AIR_IMPORTANCE = 1000                  -- Vanilla is 155
NDefines.NAI.UPGRADE_PERCENTAGE_OF_FORCES = 0.40                            -- Vanilla is 0.20
NDefines.NAI.REMOVE_OBSOLETE_TEMPLATE_DAYS = 60                             -- Vanilla is 180
-- Naval AI
NDefines.NAI.MAX_FULLY_TRAINED_SHIP_RATIO_FOR_TRAINING = 0.95				-- Vanilla is 0.7

-- Production AI
NDefines.NAI.REFIT_SHIP_PERCENTAGE_OF_FORCES = 0.3							-- Vanilla is 0.1
NDefines.NAI.DESIRE_USE_XP_TO_UPDATE_LAND_TEMPLATE = 2.5                   -- Vanilla is 2 - AI wants to upgrade its templates slightly more
NDefines.NAI.DESIRE_USE_XP_TO_UPGRADE_LAND_EQUIPMENT = 1.25                  -- Vanilla is 1 - AI wants to upgrade its land eq slightly more
NDefines.NAI.DESIRE_USE_XP_TO_UPGRADE_NAVAL_EQUIPMENT = 1.2                 -- Vanilla is 1 - AI wants to upgrade its ships slightly more
NDefines.NAI.DESIRE_USE_XP_TO_UPGRADE_AIR_EQUIPMENT = 1.5					-- Vanilla is 1 - AI wants to upgrade its planes more

-- Supply AI
NDefines.NSupply.AI_FRONT_MINIMUM_UNITS_PER_PROVINCE_FOR_SUPPLY_CALCULATIONS = 0	-- Vanilla is 1
NDefines.NSupply.AI_FRONT_DIVISIONS_PER_SUPPLY_POINT = 0.7							-- Vanilla is 1.0
NDefines.NAITheatre.AI_THEATRE_SUPPLY_CRISIS_LIMIT = 0.25							-- Vanilla is 0.1
-- Buildings
NDefines.NBuildings.MAX_SHARED_SLOTS = 30                                   -- Vanilla is 25

-- Career Profile
NDefines.NCareerProfile.MOD_STATISTICS_GROUP = "pax_britannica_career_profile"
NDefines.NCareerProfile.MOD_STATISTICS_GROUP_NAME = "PAX_BRITANNICA_CAREER_PROFILE"
-- Ideologies
NDefines.NAI.CALL_ALLY_BASE_DESIRE = 100									-- Vanilla is 20
NDefines.NAI.CALL_ALLY_DEMOCRATIC_DESIRE = 0								-- Vanilla is 50
NDefines.NAI.CALL_ALLY_NEUTRAL_DESIRE = 0									-- Vanilla is 25
NDefines.NAI.CALL_ALLY_FASCIST_DESIRE = 0									-- Vanilla is -10
NDefines.NAI.CALL_ALLY_COMMUNIST_DESIRE = 0									-- Vanilla is 75
NDefines.NAI.CALL_ALLY_OVERLORD_INVITE_PUPPET = 100							-- Vanilla is 20
NDefines.NAI.JOIN_ALLY_BASE_DESIRE = 100									-- Vanilla is 20
NDefines.NAI.JOIN_ALLY_DEMOCRATIC_DESIRE = 0								-- Vanilla is 50
NDefines.NAI.JOIN_ALLY_NEUTRAL_DESIRE = 0									-- Vanilla is 25
NDefines.NAI.JOIN_ALLY_FASCIST_DESIRE = 0									-- Vanilla is -10
NDefines.NAI.JOIN_ALLY_COMMUNIST_DESIRE = 0									-- Vanilla is 75
NDefines.NAI.FASCISTS_BEFRIEND_FASCISTS = 0									-- Vanilla is 10
NDefines.NAI.FASCISTS_ALLY_FASCISTS = 0										-- Vanilla is 0
NDefines.NAI.FASCISTS_ANTAGONIZE_FASCISTS = 0								-- Vanilla is -10
NDefines.NAI.FASCISTS_BEFRIEND_DEMOCRACIES = 0								-- Vanilla is -25
NDefines.NAI.FASCISTS_ALLY_DEMOCRACIES = 0									-- Vanilla is -100
NDefines.NAI.FASCISTS_ANTAGONIZE_DEMOCRACIES = 0							-- Vanilla is 100
NDefines.NAI.FASCISTS_BEFRIEND_COMMUNISTS = 0								-- Vanilla is -25
NDefines.NAI.FASCISTS_ALLY_COMMUNISTS = 0									-- Vanilla is -100
NDefines.NAI.FASCISTS_ANTAGONIZE_COMMUNISTS = 0								-- Vanilla is 100
NDefines.NAI.DEMOCRACIES_BEFRIEND_FASCISTS = 0								-- Vanilla is -25
NDefines.NAI.DEMOCRACIES_ALLY_FASCISTS = 0									-- Vanilla is -50
NDefines.NAI.DEMOCRACIES_ANTAGONIZE_FASCISTS = 0							-- Vanilla is 0
NDefines.NAI.DEMOCRACIES_BEFRIEND_DEMOCRACIES = 0							-- Vanilla is 0
NDefines.NAI.DEMOCRACIES_ALLY_DEMOCRACIES = 0								-- Vanilla is 0
NDefines.NAI.DEMOCRACIES_ANTAGONIZE_DEMOCRACIES = 0							-- Vanilla is -25
NDefines.NAI.DEMOCRACIES_BEFRIEND_COMMUNISTS = 0							-- Vanilla is -25
NDefines.NAI.DEMOCRACIES_ALLY_COMMUNISTS = 0								-- Vanilla is -50
NDefines.NAI.DEMOCRACIES_ANTAGONIZE_COMMUNISTS = 0							-- Vanilla is 0
NDefines.NAI.COMMUNISTS_BEFRIEND_FASCISTS = 0								-- Vanilla is -25
NDefines.NAI.COMMUNISTS_ALLY_FASCISTS = 0									-- Vanilla is -100
NDefines.NAI.COMMUNISTS_ANTAGONIZE_FASCISTS = 0								-- Vanilla is 100
NDefines.NAI.COMMUNISTS_BEFRIEND_DEMOCRACIES = 0							-- Vanilla is -25
NDefines.NAI.COMMUNISTS_ALLY_DEMOCRACIES = 0								-- Vanilla is -50
NDefines.NAI.COMMUNISTS_ANTAGONIZE_DEMOCRACIES = 0							-- Vanilla is 10
NDefines.NAI.COMMUNISTS_BEFRIEND_COMMUNISTS = 0								-- Vanilla is 25
NDefines.NAI.COMMUNISTS_ALLY_COMMUNISTS = 0									-- Vanilla is 0
NDefines.NAI.COMMUNISTS_ANTAGONIZE_COMMUNISTS = 0							-- Vanilla is -10
