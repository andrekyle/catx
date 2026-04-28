"""
Vercel function to run database migrations
"""

from migrate_user_columns import migrate_user_columns
import json

def handler(event, context):
    """Vercel function handler for database migration"""
    try:
        success = migrate_user_columns()
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Database migration completed successfully',
                    'success': True
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Database migration failed',
                    'success': False
                })
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Migration error: {str(e)}',
                'success': False
            })
        }
