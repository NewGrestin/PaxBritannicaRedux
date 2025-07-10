country_event = { # Ceasefire p3 LINES IN THE SAND
	id = GEA_Ceasefire.3
	title = GEA_Ceasefire.3.t
	desc = GEA_Ceasefire.3.d
	picture = GFX_report_PB_PHI_Aperture

	is_triggered_only = yes
	fire_only_once = yes

	option = {
		name = GEA_Ceasefire.3.a
        PHI = {
			country_event = GEA_Ceasefire.4
		}
	}
	option = {
		name = GEA_Ceasefire.3.b
		PHI = {
			country_event = GEA_Ceasefire.5
		}
	}
	option = {
		name = GEA_Ceasefire.3.c
		PHI = {
			country_event = GEA_Ceasefire.6
		}
	}
}

country_event = { # Pro-German Option
	id = GEA_Ceasefire.4
	title = GEA_Ceasefire.4.t
	desc = GEA_Ceasefire.4.d
	picture = GFX_report_PB_PHI_Aperture

	is_triggered_only = yes
	fire_only_once = yes

	option = { #no
		name = GEA_Ceasefire.4.a
		PHI = {
		set_country_flag = DAS_LINES_NEUTRAL
		set_country_flag = DAS_LINES_DAS_NO
		}
        DAS = {
			country_event = GEA_Ceasefire.7
		}
		ai_will_do = {
			base = 20
			modifier = {
				add = -50
				DAS = {
					controls_state = 624
				}
			}
			modifier = {
				add = 50
				PHI = {
					controls_state = 628
					controls_state = 625
				}
			}
		}
	}
	option = { #yeah
		name = GEA_Ceasefire.4.b
		PHI = {
		set_country_flag = DAS_LINES_DAS
		set_country_flag = DAS_LINES_DAS_YES
		}
		DAS = {
			country_event = GEA_Ceasefire.8
		}
		ai_will_do = {
			base = 20
			modifier = {
				add = 50
				DAS = {
					controls_state = 628
					controls_state = 625
				}
			}
		}
	}
}

country_event = { # Pro-Neutral Option
	id = GEA_Ceasefire.5
	title = GEA_Ceasefire.5.t
	desc = GEA_Ceasefire.5.d
	picture = GFX_report_PB_PHI_Aperture

	is_triggered_only = yes
	fire_only_once = yes

	option = { #no
		name = GEA_Ceasefire.5.a
		PHI = {
		set_country_flag = DAS_LINES_JAPAN
		set_country_flag = DAS_LINES_NEUTRAL_NO
		}
        DAS = {
			country_event = GEA_Ceasefire.7
		}
		ai_will_do = {
			base = 100
			modifier = {
				add = 50
				DAS = {
					controls_state = 624
				}
			}
			modifier = {
				add = -50
				PHI = {
					controls_state = 628
					controls_state = 625
				}
			}
		}
	}
	option = { #yeah
		name = GEA_Ceasefire.5.b
		PHI = {
		set_country_flag = DAS_LINES_NEUTRAL
		set_country_flag = DAS_LINES_NEUTRAL_YES
		}
		DAS = {
			country_event = GEA_Ceasefire.8
		}
		ai_will_do = {
			base = 20
			modifier = {
				add = 50
				DAS = {
					controls_state = 628
					controls_state = 625
				}
			}
		}
	}
}

country_event = { # Pro-Japan Option
	id = GEA_Ceasefire.6
	title = GEA_Ceasefire.6.t
	desc = GEA_Ceasefire.6.d
	picture = GFX_report_PB_PHI_Aperture

	is_triggered_only = yes
	fire_only_once = yes

	option = { #no
		name = GEA_Ceasefire.6.a
		PHI = {
		set_country_flag = DAS_LINES_JAPAN
		}
		JAP = {
		add_to_faction = PHI
		}
        DAS = {
		    country_event = GEA_Ceasefire.11
	    }
	}
}

country_event = { # GENERIC NO OPTION
	id = GEA_Ceasefire.7
	title = GEA_Ceasefire.7.t
	desc = GEA_Ceasefire.7.d
	picture = GFX_report_PB_PHI_Aperture

	is_triggered_only = yes
	fire_only_once = yes

	option = { #no
		name = GEA_Ceasefire.7.a
		if = {
			limit = {
				PHI = {
					has_country_flag = DAS_LINES_DAS_NO
				}
			}
			DAS = {
				country_event = GEA_Ceasefire.9
			}
		}
        if = {
			limit = {
				PHI = {
					has_country_flag = NEUTRAL_LINES_DAS_NO
				}
			}
			DAS = {
				country_event = GEA_Ceasefire.10
			}
		}
	}
}

country_event = { # GENERIC YES OPTION
	id = GEA_Ceasefire.8
	title = GEA_Ceasefire.8.t
	desc = GEA_Ceasefire.8.d
	picture = GFX_report_PB_PHI_Aperture

	is_triggered_only = yes
	fire_only_once = yes

	option = { #no
		name = GEA_Ceasefire.8.a
        if = {
			limit = {
				PHI = {
					has_country_flag = DAS_LINES_DAS_YES
				}
			}
			DAS = {
				country_event = GEA_Ceasefire.11
			}
		}	
		if = {
			limit = {
				PHI = {
					has_country_flag = DAS_LINES_NEUTRAL_YES
				}
			}
			DAS = {
				country_event = GEA_Ceasefire.11
			}
		}	
	}
}

country_event = { # Round 2 of voting
	id = GEA_Ceasefire.9
	title = GEA_Ceasefire.9.t
	desc = GEA_Ceasefire.9.d
	picture = GFX_report_PB_PHI_Aperture

	is_triggered_only = yes
	fire_only_once = yes

	option = {
		name = GEA_Ceasefire.3.b
		PHI = {
			country_event = GEA_Ceasefire.5
		}
	}
	option = {
		name = GEA_Ceasefire.3.c
		PHI = {
			country_event = GEA_Ceasefire.6
		}
	}
}

country_event = { # They dont wanna be neutral???
	id = GEA_Ceasefire.10
	title = GEA_Ceasefire.10.t
	desc = GEA_Ceasefire.10.d
	picture = GFX_report_PB_PHI_Aperture

	is_triggered_only = yes
	fire_only_once = yes

	option = { #welp, we lost
		name = GEA_Ceasefire.10.a
        PHI = {
		country_event = GEA_Ceasefire.6
	    }
        DAS = {
		country_event = GEA_Ceasefire.11
	    }
	}
    option = { #ROUND 2, NO LIMITS
		name = GEA_Ceasefire.10.a
		declare_war_on = {
        target = PHI
        type = annex_everything
        }
	}
}

country_event = { # The Final Fucking Event
	id = GEA_Ceasefire.11
	title = GEA_Ceasefire.11.t
	desc = GEA_Ceasefire.11.d
	picture = GFX_report_PB_PHI_Aperture

	is_triggered_only = yes
	fire_only_once = yes

	option = { #Were Fucked
		name = GEA_Ceasefire.11.a
        if = {
			limit = {
				PHI = {
					has_country_flag = DAS_LINES_DAS
				}
			}
			PHI = {
				set_cosmetic_tag = PHI_German
			}
            if = {
				limit = {
					DAS = {
						controls_state = 624
					}
				}
				PHI = {
					transfer_state = 624
				}
			}
            if = {
				limit = {
					DAS = {
						controls_state = 628
					}
				}
				PHI = {
					transfer_state = 628
				}
			}
            if = {
				limit = {
					DAS = {
						controls_state = 626
					}
				}
				PHI = {
					transfer_state = 626
				}
			}
			if = {
				limit = {
					DAS = {
						controls_state = 627
					}
				}
				PHI = {
					transfer_state = 627
				}
			}
			puppet = {
				target = PHI
				end_wars = no
			}
			remove_ideas = PB_Colonial_Insurrection
		}
        else_if = {
			limit = {
				PHI = {
					has_country_flag = DAS_LINES_NEUTRAL
				}
			}
            if = {
				limit = {
					DAS = {
						controls_state = 624
					}
				}
				PHI = {
					transfer_state = 624
				}
			}
            if = {
				limit = {
					DAS = {
						controls_state = 628
					}
				}
				PHI = {
					transfer_state = 628
				}
			}
            if = {
				limit = {
					DAS = {
						controls_state = 625
					}
				}
				PHI = {
					transfer_state = 625
				}
			}
			if = {
				limit = {
					DAS = {
						controls_state = 627
					}
				}
				PHI = {
					transfer_state = 627
				}
			}
            if = {
				limit = {
					DAS = {
						controls_state = 626
					}
				}
				PHI = {
					transfer_state = 626
				}
			}
			PHI = {
				set_cosmetic_tag = PHI
			}
			DAS = {
			    give_guarantee = PHI
			}
            PHI = {
			    give_guarantee = PHI
			}
		}
        else = {
			limit = {
				PHI = {
					has_country_flag = DAS_LINES_JAPAN
				}
			}
			if = {
				limit = {
					DAS = {
						controls_state = 624
					}
				}
				PHI = {
					transfer_state = 624
				}
			}
            if = {
				limit = {
					DAS = {
						controls_state = 628
					}
				}
				PHI = {
					transfer_state = 628
				}
			}
            if = {
				limit = {
					DAS = {
						controls_state = 625
					}
				}
				PHI = {
					transfer_state = 625
				}
			}
			if = {
				limit = {
					DAS = {
						controls_state = 627
					}
				}
				PHI = {
					transfer_state = 627
				}
			}
            if = {
				limit = {
					DAS = {
						controls_state = 626
					}
				}
				PHI = {
					transfer_state = 626
				}
			}
			PHI = {
				set_cosmetic_tag = PHI
			}
		}
	}
}