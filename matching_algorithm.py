from django.db.models import Q, Prefetch
from django.core.cache import cache
from django.db import transaction
from .models import Mentor, Startup, MentorMatch, EMNUser
from eureka25.models import Idea
from difflib import SequenceMatcher
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MatchingConfig:
    """Configuration class for matching parameters"""
    SECTOR_WEIGHTS: List[float] = None
    FUZZY_THRESHOLD: float = 0.7
    DEFAULT_SCORE: float = 25
    MIN_SCORE: float = 15
    HIGH_QUALITY_THRESHOLD: float = 70
    CACHE_TIMEOUT: int = 3600  # 1 hour
    BATCH_SIZE: int = 100

    def __post_init__(self):
        if self.SECTOR_WEIGHTS is None:
            self.SECTOR_WEIGHTS = [0.5, 0.3, 0.2]


class EMNMatchingAlgorithm:
    
    # Mentor sectors mapped to startup sectors with compatibility scores
    SECTOR_MAPPING = {
        'blockchain': {
            'dlt/blockchain': 100, 'ai': 85, 'it': 80, 'fintech': 75, 'saas': 70, 'big data': 65,
            'hardware': 60, 'security': 80, 'supply chain': 50, 'manufacturing': 40
        },
        'fmcg': {
            'fmcg': 100, 'e-commerce': 90, 'manufacturing': 85, 'logistics': 80, 'supply chain': 85,
            'agriculture': 70, 'chemicals': 75, 'foodtech': 80, 'consult': 60
        },
        'saas': {
            'saas': 100, 'it': 95, 'ai': 85, 'big data': 80, 'edutech': 85, 'fintech': 75,
            'healthcare': 70, 'consult': 80, 'security': 75, 'e-commerce': 65
        },
        'foodtech': {
            'foodtech': 100, 'agriculture': 90, 'fmcg': 85, 'logistics': 75, 'supply chain': 70,
            'biotech': 65, 'e-commerce': 70, 'manufacturing': 60
        },
        'edutech': {
            'edutech': 100, 'saas': 85, 'it': 80, 'ai': 75, 'others': 60, 'consult': 65
        },
        'fintech': {
            'fintech': 100, 'dlt/blockchain': 90, 'ai': 80, 'saas': 75, 'it': 75, 'big data': 70,
            'security': 85, 'e-commerce': 60
        },
        'biotech': {
            'biotech': 100, 'healthcare': 95, 'chemicals': 85, 'agriculture': 70, 'wearable tech': 75,
            'manufacturing': 60, 'ai': 65
        },
        'ecommerce': {
            'e-commerce': 100, 'fmcg': 85, 'logistics': 90, 'supply chain': 85, 'saas': 70,
            'fintech': 65, 'it': 60, 'manufacturing': 55
        },
        'healthcare': {
            'healthcare': 100, 'biotech': 95, 'wearable tech': 90, 'iot': 80, 'ai': 75,
            'saas': 65, 'it': 60
        },
        'consulting': {
            'consult': 100, 'saas': 85, 'it': 80, 'big data': 75, 'ai': 70, 'fintech': 65,
            'manufacturing': 60, 'healthcare': 55
        },
        'agriculture': {
            'agriculture': 100, 'foodtech': 90, 'iot': 80, 'biotech': 70, 'supply chain': 65,
            'logistics': 60, 'energy': 75, 'manufacturing': 55
        },
        'iot': {
            'iot': 100, 'wearable tech': 95, 'hardware': 90, 'it': 85, 'ai': 80, 'healthcare': 75,
            'manufacturing': 70, 'agriculture': 65, 'security': 70
        },
        'manufacturing': {
            'manufacturing': 100, 'chemicals': 85, 'hardware': 80, 'supply chain': 85, 'logistics': 75,
            'fmcg': 70, 'iot': 65, 'ai': 60, 'energy': 70
        },
        'greentech': {
            'energy': 100, 'agriculture': 75, 'manufacturing': 70, 'ev and infrastructure': 95,
            'iot': 65, 'chemicals': 60, 'supply chain': 55
        },
        'it': {
            'it': 100, 'saas': 95, 'ai': 85, 'big data': 85, 'dlt/blockchain': 80, 'hardware': 75,
            'security': 90, 'iot': 70, 'fintech': 65
        },
        'wearable': {
            'wearable tech': 100, 'iot': 95, 'healthcare': 90, 'hardware': 85, 'ai': 70,
            'it': 65, 'manufacturing': 55
        },
        'chemical': {
            'chemicals': 100, 'biotech': 85, 'manufacturing': 85, 'energy': 75, 'agriculture': 60,
            'fmcg': 70, 'healthcare': 55
        },
        'bigdata': {
            'big data': 100, 'ai': 95, 'it': 90, 'saas': 85, 'fintech': 75, 'consult': 80,
            'healthcare': 65, 'e-commerce': 60
        },
        'social': {
            'others': 100, 'edutech': 80, 'healthcare': 70, 'agriculture': 65, 'consult': 60
        },
        'logistics': {
            'logistics': 100, 'supply chain': 95, 'e-commerce': 90, 'fmcg': 80, 'manufacturing': 75,
            'mobility': 85, 'agriculture': 60
        }
    }

    def __init__(self, config: MatchingConfig = None):
        self.config = config or MatchingConfig()
        self._build_reverse_mapping()
        self._normalize_sector_mapping()

    def _build_reverse_mapping(self):
        """Build reverse mapping from the main sector mapping"""
        self.REVERSE_SECTOR_MAPPING = {}
        
        for source_sector, target_dict in self.SECTOR_MAPPING.items():
            for target_sector, score in target_dict.items():
                if target_sector not in self.REVERSE_SECTOR_MAPPING:
                    self.REVERSE_SECTOR_MAPPING[target_sector] = {}
                self.REVERSE_SECTOR_MAPPING[target_sector][source_sector] = score

        # Combined mapping that includes both directions
        self.COMBINED_SECTOR_MAPPING = {**self.SECTOR_MAPPING, **self.REVERSE_SECTOR_MAPPING}

    def _normalize_sector_mapping(self):
        """Normalize sector mapping keys to lowercase for case-insensitive matching"""
        normalized = {}
        for key, value_dict in self.COMBINED_SECTOR_MAPPING.items():
            normalized[key.lower().strip()] = {
                k.lower().strip(): v for k, v in value_dict.items()
            }
        self.SECTOR_MAPPING = normalized

    def _get_clean_sectors(self, *sectors) -> List[str]:
        """Clean and normalize sector names"""
        clean_sectors = []
        for sector in sectors:
            if sector and isinstance(sector, str):
                clean_sector = sector.lower().strip()
                if clean_sector:
                    clean_sectors.append(clean_sector)
        return clean_sectors

    def _calculate_sector_score(self, mentor: Mentor, startup: Startup) -> float:
        """
        Calculate sector compatibility score based on all 3 sectors with proper weighting
        """
        try:
            # Get mentor sectors with validation
            mentor_sectors = self._get_clean_sectors(
                mentor.preferred_sector_1,
                mentor.preferred_sector_2,
                mentor.preferred_sector_3
            )

            # Get startup sectors with validation
            startup_sectors = []
            if startup.idea:
                startup_sectors = self._get_clean_sectors(
                    startup.idea.sector_1,
                    startup.idea.sector_2,
                    startup.idea.sector_3
                )

            # Handle edge cases
            if not mentor_sectors:
                return self.config.DEFAULT_SCORE
            
            if not startup_sectors:
                return self.config.MIN_SCORE

            # Calculate comprehensive sector compatibility matrix
            total_score = 0
            total_weight = 0
            
            # For each mentor sector, find best match with startup sectors
            for i, mentor_sector in enumerate(mentor_sectors):
                mentor_weight = (self.config.SECTOR_WEIGHTS[i] 
                               if i < len(self.config.SECTOR_WEIGHTS) 
                               else 0.1)
                
                best_match_score = 0
                
                # Check against all startup sectors
                for j, startup_sector in enumerate(startup_sectors):
                    startup_weight = (self.config.SECTOR_WEIGHTS[j] 
                                    if j < len(self.config.SECTOR_WEIGHTS) 
                                    else 0.1)
                    
                    # Calculate compatibility score for this pair
                    pair_score = self._get_sector_pair_score(mentor_sector, startup_sector)
                    weighted_pair_score = pair_score * startup_weight
                    
                    best_match_score = max(best_match_score, weighted_pair_score)
                
                total_score += best_match_score * mentor_weight
                total_weight += mentor_weight
            
            # Normalize by total weight
            if total_weight > 0:
                total_score = total_score / total_weight
            
            # Store original calculated score
            calculated_score = total_score
            
            # Store calculated score before any adjustments
            calculated_score = total_score
            
            # Handle "mentor any sector" case - fallback for very low scores
            if hasattr(mentor, 'mentor_any_sector') and mentor.mentor_any_sector and total_score < 30:
                total_score = 30

            return max(total_score, self.config.MIN_SCORE)

        except Exception as e:
            logger.error(f"Error calculating sector score: {e}")
            return self.config.MIN_SCORE

    def _get_sector_pair_score(self, mentor_sector: str, startup_sector: str) -> float:
        """Calculate compatibility score between a single mentor sector and startup sector"""
        # Exact match (case-insensitive)
        if mentor_sector == startup_sector:
            return 100.0

        # Related sector match
        if mentor_sector in self.SECTOR_MAPPING:
            related_map = self.SECTOR_MAPPING[mentor_sector]
            if startup_sector in related_map:
                return float(related_map[startup_sector])

        # Fuzzy match as fallback
        similarity = SequenceMatcher(None, mentor_sector, startup_sector).ratio()
        if similarity >= self.config.FUZZY_THRESHOLD:
            return similarity * 80.0

        return 0.0

    def calculate_match_score(self, mentor: Mentor, startup: Startup) -> Dict:
        """
        Calculate comprehensive match score with caching and error handling
        """
        cache_key = f"match_score_{mentor.id}_{startup.id}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        try:
            # Calculate individual factor scores
            sector_score = self._calculate_sector_score(mentor, startup)
            
            # Future: Add more factors here
            # experience_score = self._calculate_experience_score(mentor, startup)
            # location_score = self._calculate_location_score(mentor, startup)
            
            total_score = sector_score  # Sum all factors when implemented

            factors = {
                'sector': round(sector_score, 2),
                'calculated_score': round(sector_score, 2),  # Show actual calculated score
                'final_score': round(total_score, 2),  # Show final score after adjustments
                'raw_calculated': round(sector_score, 2),  # Raw calculated score before any boosts
                # 'experience': round(experience_score, 2),
                # 'location': round(location_score, 2)
            }

            matching_sectors = self._get_matching_sectors(mentor, startup)

            result = {
                'score': round(total_score, 2),
                'factors': factors,
                'matching_sectors': matching_sectors
            }

            # Cache the result
            cache.set(cache_key, result, self.config.CACHE_TIMEOUT)
            return result

        except Exception as e:
            logger.error(f"Error calculating match score for mentor {mentor.id}, startup {startup.id}: {e}")
            return {
                'score': self.config.MIN_SCORE,
                'factors': {
                    'sector': self.config.MIN_SCORE,
                    'calculated_score': self.config.MIN_SCORE,
                    'final_score': self.config.MIN_SCORE
                },
                'matching_sectors': []
            }

    def _get_matching_sectors(self, mentor: Mentor, startup: Startup) -> List[str]:
        """Get list of matching or related sectors with improved formatting"""
        mentor_sectors = self._get_clean_sectors(
            mentor.preferred_sector_1,
            mentor.preferred_sector_2,
            mentor.preferred_sector_3
        )

        startup_sectors = []
        if startup.idea:
            startup_sectors = self._get_clean_sectors(
                startup.idea.sector_1,
                startup.idea.sector_2,
                startup.idea.sector_3
            )

        # Direct matches
        direct_matches = list(set(mentor_sectors).intersection(set(startup_sectors)))

        # Related matches
        related_matches = []
        for mentor_sector in mentor_sectors:
            if mentor_sector in self.SECTOR_MAPPING:
                related_map = self.SECTOR_MAPPING[mentor_sector]
                for startup_sector in startup_sectors:
                    if (startup_sector in related_map and 
                        startup_sector not in direct_matches):
                        match_strength = related_map[startup_sector]
                        related_matches.append(
                            f"{mentor_sector} → {startup_sector} ({match_strength}%)"
                        )

        return direct_matches + related_matches

    def generate_matches_for_mentor(self, mentor_id: int, limit: int = 10) -> List[Tuple]:
        """Generate matches for a mentor with optimized database queries"""
        try:
            mentor = Mentor.objects.get(id=mentor_id)
            
            # Optimized query with select_related and prefetch_related
            # Get startups with dashboard access enabled
            startups = Startup.objects.select_related('registration', 'idea', 'user').filter(
                user__dashboard_access=True
            ).all()
            
            matches_with_scores = []
            
            # Process in batches to avoid memory issues
            for i in range(0, startups.count(), self.config.BATCH_SIZE):
                batch = startups[i:i + self.config.BATCH_SIZE]
                
                for startup in batch:
                    result = self.calculate_match_score(mentor, startup)
                    matches_with_scores.append((startup, result['score'], result['factors']))

            # Sort and return top matches
            matches_with_scores.sort(key=lambda x: x[1], reverse=True)
            return matches_with_scores[:limit]

        except Mentor.DoesNotExist:
            logger.error(f"Mentor with id {mentor_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error generating matches for mentor {mentor_id}: {e}")
            return []

    def generate_matches_for_startup(self, startup_id: int, limit: int = 10) -> List[Tuple]:
        """Generate matches for a startup with optimized database queries"""
        try:
            startup = Startup.objects.select_related('registration', 'idea').get(id=startup_id)
            # Only include mentors with dashboard access enabled
            mentors = Mentor.objects.select_related('user').filter(
                is_active=True,
                user__dashboard_access=True
            ).all()
            
            matches_with_scores = []
            
            # Process in batches
            for i in range(0, mentors.count(), self.config.BATCH_SIZE):
                batch = mentors[i:i + self.config.BATCH_SIZE]
                
                for mentor in batch:
                    result = self.calculate_match_score(mentor, startup)
                    matches_with_scores.append((mentor, result['score'], result['factors']))

            matches_with_scores.sort(key=lambda x: x[1], reverse=True)
            return matches_with_scores[:limit]

        except Startup.DoesNotExist:
            logger.error(f"Startup with id {startup_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error generating matches for startup {startup_id}: {e}")
            return []

    def batch_create_matches(self, mentor_ids: List[int] = None, startup_ids: List[int] = None) -> Dict:
        """
        Efficiently create matches in batches with transaction management
        """
        try:
            # Only include users with dashboard access enabled
            mentors_qs = Mentor.objects.select_related('user').filter(
                is_active=True,
                user__dashboard_access=True
            )
            startups_qs = Startup.objects.select_related('registration', 'idea', 'user').filter(
                user__dashboard_access=True
            )
            
            if mentor_ids:
                mentors_qs = mentors_qs.filter(id__in=mentor_ids)
            if startup_ids:
                startups_qs = startups_qs.filter(id__in=startup_ids)

            total_matches = 0
            high_quality_matches = 0
            matches_to_create = []

            # Process in batches to avoid memory issues
            mentors = list(mentors_qs)
            startups = list(startups_qs)

            for mentor in mentors:
                for startup in startups:
                    result = self.calculate_match_score(mentor, startup)
                    
                    matches_to_create.append(
                        MentorMatch(
                            mentor=mentor,
                            startup=startup,
                            matching_sectors=result['matching_sectors'],
                            match_score=result['score'],
                            score_factors=result['factors']
                        )
                    )
                    
                    total_matches += 1
                    if result['score'] >= self.config.HIGH_QUALITY_THRESHOLD:
                        high_quality_matches += 1

                    # Batch insert when we reach batch size
                    if len(matches_to_create) >= self.config.BATCH_SIZE:
                        self._bulk_upsert_matches(matches_to_create)
                        matches_to_create = []

            # Insert remaining matches
            if matches_to_create:
                self._bulk_upsert_matches(matches_to_create)

            return {
                'total_matches': total_matches,
                'high_quality_matches': high_quality_matches,
                'mentors_count': len(mentors),
                'startups_count': len(startups)
            }

        except Exception as e:
            logger.error(f"Error in batch_create_matches: {e}")
            raise

    @transaction.atomic
    def _bulk_upsert_matches(self, matches: List[MentorMatch]):
        """Efficiently upsert matches using bulk operations"""
        try:
            # Use bulk_create with update_conflicts for PostgreSQL
            # or implement manual upsert logic for other databases
            MentorMatch.objects.bulk_create(
                matches,
                update_conflicts=True,
                update_fields=['matching_sectors', 'match_score', 'score_factors'],
                unique_fields=['mentor', 'startup']
            )
        except Exception as e:
            # Fallback to individual updates if bulk_create with conflicts not supported
            logger.warning(f"Bulk upsert failed, falling back to individual updates: {e}")
            for match in matches:
                MentorMatch.objects.update_or_create(
                    mentor=match.mentor,
                    startup=match.startup,
                    defaults={
                        'matching_sectors': match.matching_sectors,
                        'match_score': match.match_score,
                        'score_factors': match.score_factors
                    }
                )


# Usage example:
def run_matching_algorithm():
    """Example of how to use the improved algorithm"""
    config = MatchingConfig()
    config.BATCH_SIZE = 50  # Smaller batch size for memory constraints
    
    algorithm = EMNMatchingAlgorithm(config)
    
    # Generate matches for specific mentor
    mentor_matches = algorithm.generate_matches_for_mentor(mentor_id=1, limit=10)
    
    # Generate matches for specific startup  
    startup_matches = algorithm.generate_matches_for_startup(startup_id=1, limit=10)
    
    # Batch create all matches (use carefully - can be resource intensive)
    # results = algorithm.batch_create_matches()
    
    return mentor_matches, startup_matches