#!/usr/bin/env node
/**
 * Build Error Analyzer
 * 
 * Dieses Script analysiert Next.js Build-Fehler und gibt detaillierte
 * Diagnose-Informationen aus.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const BUILD_LOG = '/tmp/build-logs/build.log';
const STATUS_LOG = '/tmp/build-logs/status.log';

class BuildErrorAnalyzer {
    constructor() {
        this.errors = [];
        this.warnings = [];
        this.stats = {
            pagesBuilt: 0,
            pagesFailed: 0,
            errors: []
        };
    }

    analyze(logContent) {
        const lines = logContent.split('\n');
        
        for (const line of lines) {
            this.analyzeLine(line);
        }

        return this.generateReport();
    }

    analyzeLine(line) {
        // Prerender-Fehler erkennen
        if (line.includes('Error occurred prerendering page')) {
            const match = line.match(/page "([^"]+)"/);
            if (match) {
                this.stats.pagesFailed++;
                this.errors.push({
                    type: 'PRERENDER_ERROR',
                    page: match[1],
                    line: line
                });
            }
        }

        // useContext Fehler
        if (line.includes('useContext') && line.includes('null')) {
            this.errors.push({
                type: 'USE_CONTEXT_ERROR',
                message: 'useContext called outside Provider (likely during SSG)',
                line: line
            });
        }

        // TypeScript Fehler
        if (line.includes('Type error:')) {
            this.errors.push({
                type: 'TYPESCRIPT_ERROR',
                line: line
            });
        }

        // Export errors
        if (line.includes('Export encountered errors')) {
            this.stats.pagesFailed = parseInt(line.match(/\d+/)?.[0] || 0);
        }

        // Success
        if (line.includes('Generating static pages') && line.includes('/')) {
            const match = line.match(/\((\d+)\/(\d+)\)/);
            if (match) {
                this.stats.pagesBuilt = parseInt(match[1]);
                this.stats.totalPages = parseInt(match[2]);
            }
        }
    }

    generateReport() {
        const report = {
            summary: {
                status: this.errors.length === 0 ? 'SUCCESS' : 'FAILED',
                pagesBuilt: this.stats.pagesBuilt,
                pagesFailed: this.stats.pagesFailed,
                errorCount: this.errors.length
            },
            errors: this.errors,
            recommendations: this.generateRecommendations()
        };

        return report;
    }

    generateRecommendations() {
        const recommendations = [];

        const hasUseContextError = this.errors.some(e => e.type === 'USE_CONTEXT_ERROR');
        const hasPrerenderError = this.errors.some(e => e.type === 'PRERENDER_ERROR');

        if (hasUseContextError) {
            recommendations.push({
                priority: 'HIGH',
                issue: 'useContext wird während SSG aufgerufen',
                solution: 'Komponenten mit useSession/useContext dynamisch importieren: const Component = dynamic(() => import("./Component"), { ssr: false })'
            });
        }

        if (hasPrerenderError) {
            recommendations.push({
                priority: 'MEDIUM',
                issue: 'Prerendering schlägt bei mehreren Pages fehl',
                solution: 'export const dynamic = "force-dynamic" in betroffenen Pages oder Layout'
            });
        }

        return recommendations;
    }

    printReport(report) {
        console.log('\n========================================');
        console.log('BUILD ERROR ANALYZER REPORT');
        console.log('========================================');
        console.log(`Status: ${report.summary.status}`);
        console.log(`Pages Built: ${report.summary.pagesBuilt}/${report.summary.totalPages || '?'}`);
        console.log(`Errors: ${report.summary.errorCount}`);
        console.log('========================================\n');

        if (report.errors.length > 0) {
            console.log('ERRORS:');
            report.errors.forEach((error, i) => {
                console.log(`\n${i + 1}. [${error.type}]`);
                if (error.page) console.log(`   Page: ${error.page}`);
                if (error.message) console.log(`   Message: ${error.message}`);
                console.log(`   Line: ${error.line?.substring(0, 100)}...`);
            });
        }

        if (report.recommendations.length > 0) {
            console.log('\n\nRECOMMENDATIONS:');
            report.recommendations.forEach((rec, i) => {
                console.log(`\n${i + 1}. [${rec.priority}] ${rec.issue}`);
                console.log(`   Solution: ${rec.solution}`);
            });
        }

        console.log('\n========================================\n');
    }
}

// Main
if (require.main === module) {
    const analyzer = new BuildErrorAnalyzer();
    
    try {
        // Versuche Log-Datei zu lesen
        if (fs.existsSync(BUILD_LOG)) {
            const logContent = fs.readFileSync(BUILD_LOG, 'utf-8');
            const report = analyzer.analyze(logContent);
            analyzer.printReport(report);
            
            // Speichere Report
            fs.writeFileSync('/tmp/build-logs/report.json', JSON.stringify(report, null, 2));
            
            process.exit(report.summary.status === 'SUCCESS' ? 0 : 1);
        } else {
            console.log('No build log found');
            process.exit(1);
        }
    } catch (error) {
        console.error('Analyzer error:', error);
        process.exit(1);
    }
}

module.exports = { BuildErrorAnalyzer };
